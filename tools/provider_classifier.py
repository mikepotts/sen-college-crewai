"""
Provider Type Classification and Normalization.

Since the provider_type column in the database is currently unpopulated,
this module infers provider types from the provider name and other attributes.
"""

import re
from typing import Dict, Any, Literal

# Provider type constants
ProviderType = Literal["FE_COLLEGE", "SIXTH_FORM_COLLEGE", "TRAINING_PROVIDER", "SCHOOL", "SPECIALIST", "UNKNOWN"]

# Keywords for classification
FE_COLLEGE_PATTERNS = [
    r"\bcollege\b(?! school)",  # "college" but not "college school"
    r"\bcommunity college\b",
    r"\bfurther education\b",
    r"\bfe college\b",
    r"\btechnology college\b(?=.*(?:and|&))",  # "X and Y Technology College"
]

SIXTH_FORM_PATTERNS = [
    r"\bsixth form college\b",
    r"\bs\.?f\.?c\.?\b",
]

SCHOOL_PATTERNS = [
    r"\bschool\b",
    r"\bacademy\b",
    r"\bgrammar\b",
    r"\bprimary\b",
    r"\bsecondary\b",
    r"\bhigh school\b",
]

TRAINING_PROVIDER_PATTERNS = [
    r"\btraining\b",
    r"\bapprenticeships?\b",
    r"\bskills\b",
    r"\bltd\.?$",  # Many training providers are Ltd companies
    r"\blimited\b",
    r"\blearning\b(?!.*school)",
]

SPECIALIST_PATTERNS = [
    r"\bspecialist\b",
    r"\bsend\b",
    r"\binclusive\b",
]


def classify_provider(provider_row: Dict[str, Any]) -> str:
    """
    Classify a provider based on available information.
    
    Priority order:
    1. Specialist (if marked or detected)
    2. Sixth Form College
    3. FE College
    4. School
    5. Training Provider
    6. Unknown
    
    Args:
        provider_row: Provider data dictionary with at least 'name' field
        
    Returns:
        Provider type string: FE_COLLEGE, SIXTH_FORM_COLLEGE, TRAINING_PROVIDER, SCHOOL, SPECIALIST, or UNKNOWN
    """
    name = provider_row.get("name", "").strip()
    if not name:
        return "UNKNOWN"
    
    name_lower = name.lower()
    
    # Check for explicit specialist markers
    if provider_row.get("is_specialist"):
        return "SPECIALIST"
    
    # Check for sixth form college (specific type of college)
    if any(re.search(pattern, name_lower) for pattern in SIXTH_FORM_PATTERNS):
        return "SIXTH_FORM_COLLEGE"
    
    # Check for FE college
    if any(re.search(pattern, name_lower) for pattern in FE_COLLEGE_PATTERNS):
        # Make sure it's not a school with "college" in the name
        if not any(re.search(pattern, name_lower) for pattern in SCHOOL_PATTERNS):
            return "FE_COLLEGE"
    
    # Check for school
    if any(re.search(pattern, name_lower) for pattern in SCHOOL_PATTERNS):
        return "SCHOOL"
    
    # Check for training provider
    if any(re.search(pattern, name_lower) for pattern in TRAINING_PROVIDER_PATTERNS):
        return "TRAINING_PROVIDER"
    
    # Check for specialist indicators in name
    if any(re.search(pattern, name_lower) for pattern in SPECIALIST_PATTERNS):
        return "SPECIALIST"
    
    # Default to unknown
    return "UNKNOWN"


def should_include_provider(provider_row: Dict[str, Any], target_settings: list) -> bool:
    """
    Determine if a provider should be included based on target settings.
    
    Args:
        provider_row: Provider data dictionary
        target_settings: List of desired provider types from intent (e.g., ["FE_COLLEGE", "TRAINING_PROVIDER"])
        
    Returns:
        True if provider should be included, False otherwise
    """
    provider_type = classify_provider(provider_row)
    
    # Always include specialist providers
    if provider_type == "SPECIALIST":
        return True
    
    # If target settings include the provider type, include it
    if provider_type in target_settings:
        return True
    
    # Special case: SIXTH_FORM_COLLEGE might be acceptable for FE_COLLEGE search
    if "FE_COLLEGE" in target_settings and provider_type == "SIXTH_FORM_COLLEGE":
        return True
    
    # Special case: if type is UNKNOWN, be inclusive unless it's clearly not wanted
    # UNKNOWN providers could be valid FE/training providers that we couldn't classify
    if provider_type == "UNKNOWN":
        # Only exclude if we're specifically looking for schools only
        return "SCHOOL" in target_settings if target_settings == ["SCHOOL"] else True
    
    return False


def normalize_provider_type(provider_type_value: str) -> str:
    """
    Normalize a provider_type database value to a standard type.
    
    This is a placeholder for future when provider_type is populated.
    
    Args:
        provider_type_value: Raw provider_type from database
        
    Returns:
        Normalized provider type
    """
    if not provider_type_value:
        return "UNKNOWN"
    
    value_lower = provider_type_value.lower()
    
    if "fe" in value_lower or "further education" in value_lower:
        return "FE_COLLEGE"
    elif "sixth form" in value_lower:
        return "SIXTH_FORM_COLLEGE"
    elif "training" in value_lower or "apprentice" in value_lower:
        return "TRAINING_PROVIDER"
    elif "school" in value_lower:
        return "SCHOOL"
    elif "specialist" in value_lower:
        return "SPECIALIST"
    
    return "UNKNOWN"
