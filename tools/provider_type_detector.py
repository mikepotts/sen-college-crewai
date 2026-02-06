"""
Provider Type Detection and Normalization.

Since provider_type field in the database is currently NULL for most providers,
this module infers provider types from provider names and other metadata.
"""

import re
from typing import Optional, Dict, Any

from tools.intent_model import TargetSetting


# Patterns to detect FE colleges
# Note: Sixth form colleges are technically FE institutions, but we also have a separate
# SIXTH_FORM category. The SIXTH_FORM detection (more specific) takes precedence.
FE_COLLEGE_PATTERNS = [
    r'\bcollege\b',
    r'\bfe college\b',
    r'\bfurther education\b',
    r'\bgeneral fe\b',
    r'\bcommunity college\b',
]

# Patterns to detect training providers
TRAINING_PROVIDER_PATTERNS = [
    r'\btraining\b',
    r'\btraining limited\b',
    r'\btraining ltd\b',
    r'\btraining services\b',
    r'\bskills\b',
    r'\bapprenticeship\b',
    r'\bvocational\b',
    r'\bgroup training\b',
]

# Patterns to detect schools (to exclude by default)
SCHOOL_PATTERNS = [
    r'\bschool\b',
    r'\bacademy\b',
    r'\bprimary\b',
    r'\bsecondary\b',
    r'\bgrammar\b',
]

# Patterns to detect sixth forms (separate from FE colleges)
SIXTH_FORM_PATTERNS = [
    r'\bsixth form\b',
    r'\b6th form\b',
]

# Exceptions - these words might contain "school" but are not schools
SCHOOL_EXCEPTIONS = [
    r'\bschool of\b',  # e.g., "School of Art"
    r'\bdriving school\b',
    r'\btraining school\b',
]


def infer_provider_type(provider: Dict[str, Any]) -> str:
    """
    Infer provider type from provider data.
    
    Detection order (most specific first):
    1. Sixth form (specific check before general college check)
    2. School (excluding false positives)
    3. FE college (general college pattern)
    4. Training provider
    5. Fallback to S41/specialist flags
    
    Args:
        provider: Dictionary with provider data (must have 'name' field)
        
    Returns:
        One of: 'FE_COLLEGE', 'TRAINING_PROVIDER', 'SIXTH_FORM', 'SCHOOL', 'UNKNOWN'
    """
    name = provider.get("name", "").lower()
    
    # Use explicit provider_type if available and not NULL
    explicit_type = provider.get("provider_type")
    if explicit_type and explicit_type.strip():
        return normalize_provider_type(explicit_type)
    
    # Infer from name - check most specific patterns first
    
    # Check for sixth form specifically (before general college check)
    if any(re.search(pattern, name) for pattern in SIXTH_FORM_PATTERNS):
        return "SIXTH_FORM"
    
    # Check for schools (but exclude false positives)
    is_school_exception = any(re.search(pattern, name) for pattern in SCHOOL_EXCEPTIONS)
    if not is_school_exception:
        if any(re.search(pattern, name) for pattern in SCHOOL_PATTERNS):
            return "SCHOOL"
    
    # Check for FE colleges
    if any(re.search(pattern, name) for pattern in FE_COLLEGE_PATTERNS):
        return "FE_COLLEGE"
    
    # Check for training providers
    if any(re.search(pattern, name) for pattern in TRAINING_PROVIDER_PATTERNS):
        return "TRAINING_PROVIDER"
    
    # Check for specific indicators in other fields if available
    if provider.get("s41_approved"):
        # S41 approved providers are often specialist colleges
        return "FE_COLLEGE"
    
    if provider.get("is_specialist"):
        # Specialist providers are often FE or independent specialist
        return "FE_COLLEGE"
    
    return "UNKNOWN"


def normalize_provider_type(provider_type: str) -> str:
    """
    Normalize various provider_type values to standard categories.
    
    Args:
        provider_type: Raw provider type string
        
    Returns:
        Normalized type: 'FE_COLLEGE', 'TRAINING_PROVIDER', 'SIXTH_FORM', 'SCHOOL', 'UNKNOWN'
    """
    pt = provider_type.lower().strip()
    
    # FE College variations
    if any(x in pt for x in [
        "fe college", "further education", "general fe", 
        "tertiary college", "community college", "specialist college"
    ]):
        return "FE_COLLEGE"
    
    # Training provider variations
    if any(x in pt for x in [
        "training provider", "independent learning provider", "ilp",
        "apprenticeship provider", "skills provider"
    ]):
        return "TRAINING_PROVIDER"
    
    # Sixth form variations
    if any(x in pt for x in ["sixth form", "6th form"]):
        return "SIXTH_FORM"
    
    # School variations
    if any(x in pt for x in [
        "school", "academy", "primary", "secondary", 
        "special school", "maintained school"
    ]):
        return "SCHOOL"
    
    return "UNKNOWN"


def matches_target_settings(
    provider: Dict[str, Any],
    target_settings: list[TargetSetting]
) -> bool:
    """
    Check if a provider matches the target settings from intent.
    
    Args:
        provider: Provider dictionary
        target_settings: List of TargetSetting enums from intent
        
    Returns:
        True if provider matches any of the target settings
    """
    if TargetSetting.ANY in target_settings:
        return True
    
    inferred_type = infer_provider_type(provider)
    
    # Map inferred types to TargetSetting
    type_mapping = {
        "FE_COLLEGE": TargetSetting.FE_COLLEGE,
        "TRAINING_PROVIDER": TargetSetting.TRAINING_PROVIDER,
        "SIXTH_FORM": TargetSetting.SIXTH_FORM,
        "SCHOOL": TargetSetting.SCHOOL,
    }
    
    provider_target = type_mapping.get(inferred_type)
    
    # If unknown type, include it if FE_COLLEGE or TRAINING_PROVIDER are in targets
    # (benefit of the doubt for missing data)
    if provider_target is None:
        return (
            TargetSetting.FE_COLLEGE in target_settings or 
            TargetSetting.TRAINING_PROVIDER in target_settings
        )
    
    return provider_target in target_settings


def get_provider_type_label(provider: Dict[str, Any]) -> str:
    """
    Get a human-readable provider type label.
    
    Args:
        provider: Provider dictionary
        
    Returns:
        Human-readable type label
    """
    inferred_type = infer_provider_type(provider)
    
    labels = {
        "FE_COLLEGE": "FE College",
        "TRAINING_PROVIDER": "Training Provider",
        "SIXTH_FORM": "Sixth Form",
        "SCHOOL": "School",
        "UNKNOWN": "Provider",
    }
    
    return labels.get(inferred_type, "Provider")
