"""
Intent-based Matching and Ranking for Providers.

This module implements scoring and ranking logic based on extracted user intent,
including residential preferences, vocational areas, and SEND needs.
"""

from typing import Dict, Any, List, Tuple
import re


def score_provider_with_intent(
    provider: Dict[str, Any],
    intent: Dict[str, Any],
    base_score: float,
    distance_miles: float,
    max_radius: float
) -> Tuple[float, List[str]]:
    """
    Score a provider based on intent and generate match reasons.
    
    Args:
        provider: Provider data dictionary
        intent: Extracted intent dictionary
        base_score: Base score from existing scoring logic
        distance_miles: Distance to provider in miles
        max_radius: Maximum search radius
        
    Returns:
        Tuple of (final_score, match_reasons)
    """
    final_score = base_score
    match_reasons = []
    
    # Distance-based reason
    if distance_miles is not None:
        match_reasons.append(f"Located {distance_miles:.1f} miles from your location")
    
    # Residential matching
    residential_boost = _score_residential_match(provider, intent, match_reasons)
    final_score += residential_boost
    
    # SEND needs matching
    send_boost = _score_send_match(provider, intent, match_reasons)
    final_score += send_boost
    
    # Vocational areas matching
    vocational_boost = _score_vocational_match(provider, intent, match_reasons)
    final_score += vocational_boost
    
    # Provider type reason (FE/Training)
    from tools.provider_classifier import classify_provider
    provider_type = classify_provider(provider)
    if provider_type in ["FE_COLLEGE", "SIXTH_FORM_COLLEGE"]:
        match_reasons.append("Further Education college offering broad curriculum")
    elif provider_type == "TRAINING_PROVIDER":
        match_reasons.append("Specialist training provider with vocational focus")
    elif provider_type == "SPECIALIST":
        match_reasons.append("Specialist provider for learners with SEND")
    
    return final_score, match_reasons


def _score_residential_match(
    provider: Dict[str, Any],
    intent: Dict[str, Any],
    match_reasons: List[str]
) -> float:
    """
    Score and explain residential matching.
    
    Returns boost to add to score.
    """
    is_residential = bool(provider.get("is_residential"))
    residential_pref = intent.get("residential", "any")
    
    if residential_pref == "any":
        return 0.0  # No boost or penalty
    
    if residential_pref == "must":
        if is_residential:
            match_reasons.append("✓ Residential accommodation available (required)")
            return 0.3  # Significant boost
        else:
            # This provider shouldn't have been included if filtering was correct
            return -0.5  # Heavy penalty
    
    if residential_pref == "prefer":
        if is_residential:
            match_reasons.append("✓ Residential accommodation available (preferred)")
            return 0.2  # Moderate boost
        else:
            match_reasons.append("Non-residential (you preferred residential)")
            return -0.05  # Slight penalty
    
    if residential_pref == "exclude":
        if not is_residential:
            match_reasons.append("✓ Day provision (as requested)")
            return 0.1  # Small boost for matching preference
        else:
            return -0.3  # Penalty for not matching exclusion
    
    return 0.0


def _score_send_match(
    provider: Dict[str, Any],
    intent: Dict[str, Any],
    match_reasons: List[str]
) -> float:
    """
    Score and explain SEND needs matching.
    
    Returns boost to add to score.
    """
    send_needs = intent.get("send_needs", [])
    if not send_needs:
        return 0.0
    
    boost = 0.0
    
    # Boost for specialist providers
    if provider.get("is_specialist"):
        match_reasons.append("✓ Specialist provider for learners with additional needs")
        boost += 0.15
    
    # Boost for Section 41 approved
    if provider.get("s41_approved"):
        match_reasons.append("✓ Section 41 approved for SEND provision")
        boost += 0.2
    
    # If we have specific SEND needs, add general support message
    if send_needs and (provider.get("is_specialist") or provider.get("s41_approved")):
        needs_text = ", ".join(send_needs[:3])
        match_reasons.append(f"Support available for: {needs_text}")
    elif send_needs:
        # Provider might still have SEND support even if not specialist
        needs_text = ", ".join(send_needs[:2])
        match_reasons.append(f"May offer support for: {needs_text}")
        boost += 0.05  # Small boost for having SEND needs that could be matched
    
    return boost


def _score_vocational_match(
    provider: Dict[str, Any],
    intent: Dict[str, Any],
    match_reasons: List[str]
) -> float:
    """
    Score and explain vocational area matching.
    
    Uses heuristic matching based on provider name, website, and type.
    
    Returns boost to add to score.
    """
    vocational_areas = intent.get("vocational_areas", [])
    if not vocational_areas:
        return 0.0
    
    # Build searchable text from provider
    search_text_parts = [
        provider.get("name", ""),
        provider.get("provider_type", ""),
        provider.get("website", ""),
    ]
    search_text = " ".join(filter(None, search_text_parts)).lower()
    
    # Vocational area keyword mapping (from intent_extractor)
    from tools.intent_extractor import VOCATIONAL_AREAS
    
    matched_areas = []
    boost = 0.0
    
    for area in vocational_areas:
        area_keywords = VOCATIONAL_AREAS.get(area, [])
        if any(kw in search_text for kw in area_keywords):
            matched_areas.append(area)
            boost += 0.1  # Boost per matched area
    
    if matched_areas:
        areas_text = ", ".join(matched_areas).replace("_", " ").title()
        match_reasons.append(f"Likely offers: {areas_text}")
    else:
        # No direct match, but still mention the interest
        areas_text = ", ".join(vocational_areas).replace("_", " ").title()
        match_reasons.append(f"Provider may offer courses in: {areas_text}")
        boost += 0.02  # Very small boost for having vocational interest
    
    return boost


def filter_providers_by_residential(
    providers: List[Dict[str, Any]],
    residential_pref: str
) -> List[Dict[str, Any]]:
    """
    Filter providers based on residential preference.
    
    Only applies hard filtering for 'must' and 'exclude'.
    
    Args:
        providers: List of provider dictionaries
        residential_pref: "any", "must", "prefer", or "exclude"
        
    Returns:
        Filtered list of providers
    """
    if residential_pref == "any" or residential_pref == "prefer":
        # No hard filtering, just scoring/ranking will handle it
        return providers
    
    if residential_pref == "must":
        # Only include residential providers
        return [p for p in providers if p.get("is_residential")]
    
    if residential_pref == "exclude":
        # Only include non-residential providers
        return [p for p in providers if not p.get("is_residential")]
    
    return providers


def generate_intent_summary(intent: Dict[str, Any]) -> str:
    """
    Generate a human-readable summary of the extracted intent.
    
    Args:
        intent: Intent dictionary
        
    Returns:
        Summary string
    """
    parts = []
    
    # Residential
    if intent.get("residential") != "any":
        res_map = {
            "must": "Requires residential",
            "prefer": "Prefers residential",
            "exclude": "Day provision only"
        }
        parts.append(res_map.get(intent["residential"], ""))
    
    # Vocational areas
    if intent.get("vocational_areas"):
        areas = ", ".join(intent["vocational_areas"]).replace("_", " ").title()
        parts.append(f"Interested in: {areas}")
    
    # SEND needs
    if intent.get("send_needs"):
        needs = ", ".join(intent["send_needs"][:3]).replace("_", " ").title()
        parts.append(f"Support for: {needs}")
    
    # Target settings
    target = intent.get("target_settings", [])
    if target and "SCHOOL" not in target:
        parts.append("Focusing on FE colleges and training providers")
    
    if parts:
        return " | ".join(parts)
    else:
        return "General search for suitable providers"
