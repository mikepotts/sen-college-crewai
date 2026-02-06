"""
Intent Extraction Module for GenAI-driven search.

This module extracts structured intent from free-text user prompts to drive
provider matching and ranking. It supports both LLM-based extraction (using OpenAI)
and deterministic rule-based fallback when LLM is unavailable.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Literal

logger = logging.getLogger(__name__)

# Vocational area taxonomy - extensible list of supported areas
VOCATIONAL_AREAS = {
    "hospitality": ["hospitality", "catering", "chef", "cookery", "kitchen", "restaurant", "barista", "food"],
    "construction": ["construction", "building", "carpentry", "joinery", "plumbing", "electrical", "bricklaying"],
    "hair_beauty": ["hair", "beauty", "hairdressing", "barbering", "makeup", "aesthetics", "salon"],
    "computing": ["computing", "it", "digital", "programming", "software", "web", "technology", "cyber"],
    "land_based": ["agriculture", "horticulture", "animal care", "farming", "countryside", "equine", "veterinary"],
    "retail": ["retail", "customer service", "sales", "shop", "store"],
    "childcare": ["childcare", "early years", "nursery", "teaching assistant"],
    "motor_vehicle": ["motor vehicle", "automotive", "mechanic", "car repair", "vehicle maintenance"]
}

# SEND needs keywords - comprehensive list
SEND_NEEDS_KEYWORDS = {
    "autism": ["autism", "asd", "asperger", "autistic"],
    "adhd": ["adhd", "attention deficit", "hyperactivity"],
    "literacy": ["literacy", "reading", "writing", "dyslexia", "dyslexic"],
    "numeracy": ["numeracy", "maths", "dyscalculia"],
    "time_management": ["time management", "organisation", "planning", "executive function"],
    "sensory": ["sensory", "quiet", "noise", "visual", "tactile"],
    "communication": ["communication", "speech", "language", "social"],
    "physical": ["physical", "mobility", "wheelchair", "accessible"],
    "mental_health": ["anxiety", "depression", "mental health", "wellbeing"]
}

# Residential keywords
RESIDENTIAL_KEYWORDS = {
    "must": ["residential", "boarding", "live-in", "on-site accommodation", "stay at college"],
    "prefer": ["prefer residential", "ideally residential", "residential would be good"],
    "exclude": ["not residential", "no residential", "day only", "commute", "local only"]
}

# School-related keywords
SCHOOL_KEYWORDS = ["school", "sixth form", "grammar", "academy"]

# FE College keywords
FE_COLLEGE_KEYWORDS = ["college", "fe college", "further education", "community college"]

# Training provider keywords
TRAINING_PROVIDER_KEYWORDS = ["training", "apprenticeship", "vocational", "skills"]


def extract_intent(prompt: str) -> Dict[str, Any]:
    """
    Extract structured intent from user prompt.
    
    Attempts LLM-based extraction first, falls back to rule-based extraction.
    
    Args:
        prompt: User's free-text description of needs
        
    Returns:
        Intent dictionary with structure:
        {
            "target_settings": ["FE_COLLEGE", "TRAINING_PROVIDER"],  # or include "SCHOOL"
            "residential": "any" | "must" | "prefer" | "exclude",
            "vocational_areas": ["hospitality", "construction", ...],
            "send_needs": ["autism", "adhd", ...],
            "send_needs_text": "original free-text for reference",
            "confidence": "high" | "medium" | "low",
            "warnings": ["list of any warnings"],
            "extraction_method": "llm" | "fallback"
        }
    """
    api_key = os.getenv("OPENAI_API_KEY")
    
    if api_key and api_key.strip():
        # Try LLM-based extraction
        intent = _extract_with_llm(prompt, api_key)
        if intent:
            intent["extraction_method"] = "llm"
            return intent
    
    # Fallback to rule-based extraction
    logger.info("Using fallback rule-based intent extraction")
    intent = _extract_with_rules(prompt)
    intent["extraction_method"] = "fallback"
    return intent


def _extract_with_llm(prompt: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Extract intent using OpenAI LLM with strict JSON schema.
    
    Args:
        prompt: User prompt
        api_key: OpenAI API key
        
    Returns:
        Intent dictionary or None if extraction fails
    """
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        
        system_prompt = """You are an expert at understanding educational needs and preferences for young people with SEND (Special Educational Needs and Disabilities).

Your task is to extract structured intent from user descriptions to help match them with suitable education providers.

Extract the following information:
1. **target_settings**: Default to ["FE_COLLEGE", "TRAINING_PROVIDER"]. Only include "SCHOOL" if explicitly mentioned.
2. **residential**: Determine if they need/want residential (must/prefer/exclude/any).
3. **vocational_areas**: Identify career/course interests from this list: hospitality, construction, hair_beauty, computing, land_based, retail, childcare, motor_vehicle.
4. **send_needs**: Identify SEND needs from: autism, adhd, literacy, numeracy, time_management, sensory, communication, physical, mental_health.
5. **confidence**: Your confidence in the extraction (high/medium/low).
6. **warnings**: Any ambiguities or concerns.

Return ONLY valid JSON matching this exact schema:
{
  "target_settings": ["FE_COLLEGE", "TRAINING_PROVIDER"],
  "residential": "any",
  "vocational_areas": [],
  "send_needs": [],
  "send_needs_text": "",
  "confidence": "medium",
  "warnings": []
}"""

        user_message = f"Extract intent from this description:\n\n{prompt}"
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        intent = json.loads(result)
        
        # Validate and sanitize
        intent = _validate_intent(intent, prompt)
        
        logger.info(f"LLM intent extraction successful: {intent.get('confidence')} confidence")
        return intent
        
    except Exception as e:
        logger.warning(f"LLM intent extraction failed: {e}")
        return None


def _extract_with_rules(prompt: str) -> Dict[str, Any]:
    """
    Deterministic rule-based intent extraction.
    
    Uses keyword matching and pattern recognition to extract intent.
    
    Args:
        prompt: User prompt
        
    Returns:
        Intent dictionary
    """
    prompt_lower = prompt.lower()
    
    # Extract target settings
    target_settings = ["FE_COLLEGE", "TRAINING_PROVIDER"]  # Default
    if any(kw in prompt_lower for kw in SCHOOL_KEYWORDS):
        target_settings.append("SCHOOL")
    
    # Extract residential preference - check exclude first to catch negations
    residential = "any"
    
    # Check exclusion first (to catch "not residential", "no residential", etc.)
    for kw in RESIDENTIAL_KEYWORDS["exclude"]:
        if kw in prompt_lower:
            residential = "exclude"
            break
    
    # Only check "must" if not already excluded
    if residential == "any":
        for kw in RESIDENTIAL_KEYWORDS["must"]:
            if kw in prompt_lower:
                residential = "must"
                break
    
    # Check "prefer" last
    if residential == "any":
        for kw in RESIDENTIAL_KEYWORDS["prefer"]:
            if kw in prompt_lower:
                residential = "prefer"
                break
    
    # Extract vocational areas
    vocational_areas = []
    for area, keywords in VOCATIONAL_AREAS.items():
        if any(kw in prompt_lower for kw in keywords):
            vocational_areas.append(area)
    
    # Extract SEND needs
    send_needs = []
    for need, keywords in SEND_NEEDS_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            send_needs.append(need)
    
    # Determine confidence based on what we found
    confidence = "low"
    if vocational_areas or send_needs or residential != "any":
        confidence = "medium"
    if len(vocational_areas) > 0 and len(send_needs) > 0:
        confidence = "high"
    
    warnings = []
    if not vocational_areas:
        warnings.append("No specific vocational areas detected")
    if not send_needs:
        warnings.append("No specific SEND needs detected")
    
    return {
        "target_settings": target_settings,
        "residential": residential,
        "vocational_areas": vocational_areas,
        "send_needs": send_needs,
        "send_needs_text": prompt,
        "confidence": confidence,
        "warnings": warnings
    }


def _validate_intent(intent: Dict[str, Any], original_prompt: str) -> Dict[str, Any]:
    """
    Validate and sanitize LLM-extracted intent.
    
    Ensures all required fields are present with valid values.
    
    Args:
        intent: Raw LLM output
        original_prompt: Original user prompt for fallback text
        
    Returns:
        Validated intent dictionary
    """
    validated = {
        "target_settings": intent.get("target_settings", ["FE_COLLEGE", "TRAINING_PROVIDER"]),
        "residential": intent.get("residential", "any"),
        "vocational_areas": intent.get("vocational_areas", []),
        "send_needs": intent.get("send_needs", []),
        "send_needs_text": intent.get("send_needs_text", original_prompt),
        "confidence": intent.get("confidence", "medium"),
        "warnings": intent.get("warnings", [])
    }
    
    # Validate residential value
    if validated["residential"] not in ["any", "must", "prefer", "exclude"]:
        validated["residential"] = "any"
        validated["warnings"].append(f"Invalid residential value, defaulted to 'any'")
    
    # Ensure target_settings is a list
    if not isinstance(validated["target_settings"], list):
        validated["target_settings"] = ["FE_COLLEGE", "TRAINING_PROVIDER"]
        validated["warnings"].append("Invalid target_settings, using defaults")
    
    # Ensure lists are actually lists
    for field in ["vocational_areas", "send_needs", "warnings"]:
        if not isinstance(validated[field], list):
            validated[field] = []
    
    return validated
