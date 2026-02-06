"""
Intent Model for GenAI-driven provider matching.

Defines structured intent extracted from user prompts to guide search and ranking.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TargetSetting(str, Enum):
    """Type of education setting the user is looking for."""
    FE_COLLEGE = "fe_college"
    TRAINING_PROVIDER = "training_provider"
    SIXTH_FORM = "sixth_form"
    SCHOOL = "school"
    ANY = "any"


class ResidentialPreference(str, Enum):
    """User's preference for residential provision."""
    MUST = "must"  # Only show residential
    PREFER = "prefer"  # Boost residential but show all
    EXCLUDE = "exclude"  # Don't show residential
    ANY = "any"  # No preference


class ExtractedIntent(BaseModel):
    """
    Structured intent extracted from user prompt.
    
    This model captures what the user is looking for to guide search,
    filtering, and ranking of providers.
    """
    
    # Target settings (defaults to FE and training providers)
    target_settings: List[TargetSetting] = Field(
        default_factory=lambda: [TargetSetting.FE_COLLEGE, TargetSetting.TRAINING_PROVIDER],
        description="Types of education settings to include"
    )
    
    # Residential preference
    residential: ResidentialPreference = Field(
        default=ResidentialPreference.ANY,
        description="User's residential requirement/preference"
    )
    
    # Vocational interests (normalized tags)
    vocational_areas: List[str] = Field(
        default_factory=list,
        description="Vocational interest areas (e.g., hospitality_catering, it_computing)"
    )
    
    # SEND needs
    send_needs: List[str] = Field(
        default_factory=list,
        description="Identified SEND needs (e.g., autism, adhd, dyslexia)"
    )
    
    # Support needs (free text or specific)
    support_needs: List[str] = Field(
        default_factory=list,
        description="Specific support requirements (e.g., quiet_spaces, visual_schedules)"
    )
    
    # Free-text capture of support needs
    support_needs_free_text: str = Field(
        default="",
        description="Original free-text description of support needs"
    )
    
    # Confidence and metadata
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the extraction (0.0-1.0)"
    )
    
    notes: str = Field(
        default="",
        description="Any warnings or clarifications about the extraction"
    )
    
    # Original prompt for reference
    original_prompt: str = Field(
        default="",
        description="The original user prompt"
    )


# Vocational taxonomy - extensible list of recognized areas
VOCATIONAL_TAXONOMY = {
    "hospitality_catering": [
        "hospitality", "catering", "cooking", "chef", "kitchen", 
        "culinary", "restaurant", "food service", "barista", "bakery"
    ],
    "it_computing": [
        "it", "computing", "computer", "programming", "coding", 
        "software", "digital", "technology", "cyber", "web"
    ],
    "construction": [
        "construction", "building", "carpentry", "plumbing", 
        "electrical", "bricklaying", "joinery"
    ],
    "creative_arts": [
        "art", "design", "creative", "media", "photography", 
        "music", "performing arts", "drama", "theatre"
    ],
    "health_care": [
        "health", "care", "nursing", "medical", "healthcare", 
        "childcare", "social care", "therapy"
    ],
    "business_admin": [
        "business", "administration", "admin", "office", 
        "management", "finance", "accounting"
    ],
    "engineering": [
        "engineering", "mechanical", "automotive", "motor vehicle"
    ],
    "retail_customer_service": [
        "retail", "customer service", "sales", "shop"
    ],
    "hairdressing_beauty": [
        "hairdressing", "beauty", "makeup", "aesthetics", "barbering"
    ],
    "sports_fitness": [
        "sport", "sports", "fitness", "coaching", "pe", "physical education"
    ]
}


# Common SEND keywords for detection
SEND_KEYWORDS = {
    "autism": ["autism", "asd", "asperger", "autistic"],
    "adhd": ["adhd", "add", "attention deficit"],
    "dyslexia": ["dyslexia", "dyslexic"],
    "dyscalculia": ["dyscalculia"],
    "dyspraxia": ["dyspraxia", "dcd"],
    "speech_language": ["speech", "language difficulties", "communication"],
    "visual_impairment": ["visual impairment", "blind", "partially sighted", "vi"],
    "hearing_impairment": ["hearing impairment", "deaf", "hard of hearing", "hi"],
    "physical_disability": ["physical disability", "wheelchair", "mobility"],
    "learning_disability": ["learning disability", "learning difficulties", "moderate learning difficulty", "mld", "severe learning difficulty", "sld"],
    "mental_health": ["anxiety", "depression", "mental health", "ocd"],
}


# Common support needs keywords
SUPPORT_KEYWORDS = {
    "quiet_spaces": ["quiet", "quiet space", "quiet room", "sensory room"],
    "visual_schedules": ["visual schedule", "visual timetable", "visual support"],
    "small_groups": ["small group", "small class", "reduced class size"],
    "1to1_support": ["one to one", "1:1", "1-1", "individual support", "learning support assistant", "lsa"],
    "reading_support": ["reading support", "literacy", "reading help"],
    "organization_support": ["organization", "planning", "time management", "executive function"],
    "communication_support": ["communication support", "makaton", "pecs", "aac"],
    "physical_access": ["wheelchair access", "accessible", "accessibility", "lift"],
}
