
import re
from typing import Dict, Any, List, Optional

# Import will be done inside function to avoid circular imports
# from tools.intent_model import ExtractedIntent, ResidentialPreference, VOCATIONAL_TAXONOMY

HOSPITALITY_KEYWORDS=[r"hospitality",r"catering",r"professional cookery",r"kitchen",r"chef",r"restaurant",r"barista",r"food"]
SEND_KEYWORDS=[r"ehcp",r"ehc plan",r"send",r"inclusive learning",r"foundation learning",r"high needs",r"additional learning support",r"reasonable adjustments",r"autism",r"adhd",r"quiet",r"sensory"]

def keyword_hits(text: str, patterns) -> int:
    if not text: return 0
    t=text.lower(); hits=0
    for p in patterns:
        if re.search(p,t): hits+=1
    return hits

def normalize(v: float, m: float) -> float:
    if m<=0: return 0.0
    return max(0.0, min(1.0, v/m))

def blended_score(distance_miles: float, radius_miles: float, aspiration_hits: int, send_hits: int, cfg):
    d_comp = 1.0 - (distance_miles / max(radius_miles, 0.0001))
    d_comp = max(0.0, min(1.0, d_comp))
    a_comp = normalize(aspiration_hits, 10)
    s_comp = normalize(send_hits, 10)
    score = cfg.w_distance*d_comp + cfg.w_aspiration*a_comp + cfg.w_send_fit*s_comp
    return score, d_comp, a_comp, s_comp


def intent_based_score(
    provider: Dict[str, Any],
    distance_miles: float,
    radius_miles: float,
    intent: Optional[Any],  # ExtractedIntent or None
    cfg
) -> tuple[float, Dict[str, float], List[str]]:
    """
    Calculate score based on extracted intent with match reasons.
    
    Args:
        provider: Provider dictionary
        distance_miles: Distance from user
        radius_miles: Search radius
        intent: Extracted intent from prompt (None for legacy behavior)
        cfg: Scoring configuration
        
    Returns:
        Tuple of (score, breakdown_dict, match_reasons_list)
    """
    from tools.intent_model import ExtractedIntent, ResidentialPreference, VOCATIONAL_TAXONOMY
    
    match_reasons = []
    
    # Base distance component
    d_comp = 1.0 - (distance_miles / max(radius_miles, 0.0001))
    d_comp = max(0.0, min(1.0, d_comp))
    
    # If no intent, use legacy scoring
    if not intent:
        # Legacy keyword matching
        text_parts = [provider.get("name", ""), provider.get("provider_type", "")]
        text = " ".join(filter(None, text_parts))
        a_hits = keyword_hits(text, HOSPITALITY_KEYWORDS)
        s_hits = keyword_hits(text, SEND_KEYWORDS)
        
        a_comp = normalize(a_hits, 10)
        s_comp = normalize(s_hits, 10)
        
        score = cfg.w_distance*d_comp + cfg.w_aspiration*a_comp + cfg.w_send_fit*s_comp
        
        breakdown = {
            "distance_component": round(d_comp, 4),
            "aspiration_component": round(a_comp, 4),
            "sendfit_component": round(s_comp, 4),
        }
        
        if distance_miles:
            match_reasons.append(f"Located {distance_miles} miles from your location")
        
        return score, breakdown, match_reasons
    
    # Intent-based scoring
    base_score = 0.0
    breakdown = {}
    
    # 1. Distance component (same as before)
    base_score += cfg.w_distance * d_comp
    breakdown["distance_component"] = round(d_comp, 4)
    
    if distance_miles:
        match_reasons.append(f"Located {distance_miles} miles from your location")
    
    # 2. Residential boost/penalty
    residential_boost = 0.0
    if intent.residential == ResidentialPreference.MUST:
        if provider.get("is_residential"):
            residential_boost = 0.3  # Strong boost
            match_reasons.append("✓ Residential provision available (required)")
        else:
            residential_boost = -0.5  # Strong penalty
            match_reasons.append("⚠ Not residential (requirement not met)")
    elif intent.residential == ResidentialPreference.PREFER:
        if provider.get("is_residential"):
            residential_boost = 0.15  # Moderate boost
            match_reasons.append("✓ Residential provision available (preferred)")
    elif intent.residential == ResidentialPreference.EXCLUDE:
        if not provider.get("is_residential"):
            residential_boost = 0.05  # Small boost for matching preference
        else:
            residential_boost = -0.2  # Penalty for not matching
    
    base_score += residential_boost
    breakdown["residential_boost"] = round(residential_boost, 4)
    
    # 3. Vocational area matching (text-based heuristics)
    vocational_score = 0.0
    if intent.vocational_areas:
        provider_text = " ".join([
            provider.get("name", ""),
            provider.get("website", ""),
        ]).lower()
        
        matched_areas = []
        for area in intent.vocational_areas:
            # Get keywords for this area
            keywords = VOCATIONAL_TAXONOMY.get(area, [])
            for keyword in keywords:
                if keyword.lower() in provider_text:
                    matched_areas.append(area)
                    break
        
        if matched_areas:
            # Boost based on number of matched areas
            vocational_score = min(0.3, len(matched_areas) * 0.15)
            area_labels = [a.replace("_", " ").title() for a in matched_areas]
            match_reasons.append(f"✓ May offer courses in: {', '.join(area_labels)}")
        else:
            # Neutral score if no matches (they might still offer it)
            vocational_score = 0.0
            area_labels = [a.replace("_", " ").title() for a in intent.vocational_areas[:2]]
            match_reasons.append(f"Vocational interest: {', '.join(area_labels)}")
    
    base_score += cfg.w_aspiration * vocational_score
    breakdown["vocational_component"] = round(vocational_score, 4)
    
    # 4. SEND support matching
    send_score = 0.0
    if intent.send_needs or intent.support_needs:
        # Boost for s41 approved
        if provider.get("s41_approved"):
            send_score += 0.4
            match_reasons.append("✓ Section 41 approved for SEND provision")
        
        # Boost for specialist provision
        if provider.get("is_specialist"):
            send_score += 0.3
            match_reasons.append("✓ Specialist SEND provider")
        
        # Even if no specific flags, assume some SEND support
        if send_score == 0.0:
            send_score = 0.2
            match_reasons.append("Provider likely offers SEND support")
        
        # Mention specific needs
        if intent.send_needs:
            needs_text = ", ".join(intent.send_needs[:3]).replace("_", " ").title()
            match_reasons.append(f"Support needs: {needs_text}")
    else:
        # Baseline SEND score for all providers
        send_score = 0.1
    
    base_score += cfg.w_send_fit * send_score
    breakdown["send_component"] = round(send_score, 4)
    
    # 5. Provider type indicator (not scored, just for display)
    from tools.provider_type_detector import get_provider_type_label
    provider_type_label = get_provider_type_label(provider)
    if provider_type_label != "Provider":
        match_reasons.append(f"Type: {provider_type_label}")
    
    # Ensure score is in reasonable range [0, 1]
    final_score = max(0.0, min(1.0, base_score))
    
    return final_score, breakdown, match_reasons
