"""
Intent Extraction using LLM with deterministic fallback.

Extracts structured intent from user prompts to guide provider matching.
"""

import os
import logging
import re
from typing import Optional

from crewai import Agent, Task, Crew, Process, LLM

from tools.intent_model import (
    ExtractedIntent,
    TargetSetting,
    ResidentialPreference,
    VOCATIONAL_TAXONOMY,
    SEND_KEYWORDS,
    SUPPORT_KEYWORDS,
)

logger = logging.getLogger(__name__)


def extract_intent_from_prompt(prompt: str) -> ExtractedIntent:
    """
    Extract structured intent from a natural language prompt.
    
    Uses LLM (OpenAI via CrewAI) when available, with deterministic
    keyword-based fallback if LLM is not configured.
    
    Args:
        prompt: Natural language description of needs and preferences
        
    Returns:
        ExtractedIntent with extracted information
    """
    if not prompt or not prompt.strip():
        return ExtractedIntent(
            original_prompt=prompt or "",
            notes="Empty prompt provided"
        )
    
    # Try LLM extraction first
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            intent = _extract_with_llm(prompt, api_key)
            if intent:
                return intent
        except Exception as e:
            logger.warning(f"LLM intent extraction failed: {e}, falling back to keyword rules")
    
    # Fallback to deterministic keyword extraction
    return _extract_with_keywords(prompt)


def _extract_with_llm(prompt: str, api_key: str) -> Optional[ExtractedIntent]:
    """Extract intent using LLM (OpenAI via CrewAI)."""
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    try:
        llm = LLM(
            model=f"openai/{model_name}",
            api_key=api_key,
            temperature=0.2  # Low temperature for consistent extraction
        )
        
        agent = Agent(
            role="SEND Education Intent Analyst",
            goal="Extract structured search intent from natural language descriptions",
            backstory=(
                "You are an expert in UK post-16 SEND education provision. "
                "You understand different types of settings (FE colleges, training providers, "
                "sixth forms, schools), residential vs non-residential provision, "
                "vocational areas, and SEND needs. You extract precise, actionable "
                "search parameters from parent/guardian descriptions."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False
        )
        
        # Build vocational taxonomy description
        voc_examples = ", ".join([
            f"{key} ({', '.join(words[:3])})" 
            for key, words in list(VOCATIONAL_TAXONOMY.items())[:5]
        ])
        
        task = Task(
            description=(
                f"Analyze this search request and extract structured intent:\n\n"
                f'"{prompt}"\n\n'
                f"Extract:\n"
                f"1. TARGET_SETTINGS: What types of providers? Options: fe_college, training_provider, sixth_form, school, or any. "
                f"Default to fe_college+training_provider unless schools/sixth forms are mentioned.\n"
                f"2. RESIDENTIAL: Is residential provision wanted? Options: must (only residential), prefer (boost residential), exclude (no residential), any (no preference)\n"
                f"3. VOCATIONAL_AREAS: Career/course interests. Normalize to: {voc_examples}, etc.\n"
                f"4. SEND_NEEDS: Diagnosed conditions like autism, adhd, dyslexia, etc.\n"
                f"5. SUPPORT_NEEDS: Specific support like quiet_spaces, visual_schedules, small_groups, 1to1_support, etc.\n"
                f"6. CONFIDENCE: Your confidence in the extraction (0.0-1.0)\n"
            ),
            expected_output=(
                "Respond in this EXACT format:\n"
                "TARGET_SETTINGS: comma-separated list or 'default'\n"
                "RESIDENTIAL: must|prefer|exclude|any\n"
                "VOCATIONAL_AREAS: comma-separated normalized tags or 'none'\n"
                "SEND_NEEDS: comma-separated conditions or 'none'\n"
                "SUPPORT_NEEDS: comma-separated normalized tags or 'none'\n"
                "CONFIDENCE: 0.0-1.0\n"
                "NOTES: any important notes or warnings"
            ),
            agent=agent
        )
        
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        
        # Parse the result
        intent = _parse_llm_result(str(result), prompt)
        logger.info(f"LLM intent extraction successful: {len(intent.vocational_areas)} vocational areas, {len(intent.send_needs)} SEND needs")
        return intent
        
    except Exception as e:
        logger.error(f"LLM intent extraction error: {e}", exc_info=True)
        return None


def _parse_llm_result(result: str, original_prompt: str) -> ExtractedIntent:
    """Parse the LLM output into ExtractedIntent."""
    lines = result.strip().split('\n')
    
    # Defaults
    target_settings = [TargetSetting.FE_COLLEGE, TargetSetting.TRAINING_PROVIDER]
    residential = ResidentialPreference.ANY
    vocational_areas = []
    send_needs = []
    support_needs = []
    confidence = 0.8
    notes = ""
    
    for line in lines:
        line = line.strip()
        
        if line.startswith("TARGET_SETTINGS:"):
            value = line.replace("TARGET_SETTINGS:", "").strip().lower()
            if value != "default" and value != "none":
                target_settings = []
                for item in value.split(","):
                    item = item.strip()
                    if "fe" in item or "college" in item and "sixth" not in item:
                        target_settings.append(TargetSetting.FE_COLLEGE)
                    elif "training" in item or "provider" in item:
                        target_settings.append(TargetSetting.TRAINING_PROVIDER)
                    elif "sixth" in item:
                        target_settings.append(TargetSetting.SIXTH_FORM)
                    elif "school" in item:
                        target_settings.append(TargetSetting.SCHOOL)
                    elif "any" in item:
                        target_settings = [TargetSetting.ANY]
                        break
                # Ensure defaults if empty
                if not target_settings:
                    target_settings = [TargetSetting.FE_COLLEGE, TargetSetting.TRAINING_PROVIDER]
        
        elif line.startswith("RESIDENTIAL:"):
            value = line.replace("RESIDENTIAL:", "").strip().lower()
            if "must" in value or "only" in value:
                residential = ResidentialPreference.MUST
            elif "prefer" in value or "want" in value:
                residential = ResidentialPreference.PREFER
            elif "exclude" in value or "not" in value or "no" in value:
                residential = ResidentialPreference.EXCLUDE
            else:
                residential = ResidentialPreference.ANY
        
        elif line.startswith("VOCATIONAL_AREAS:"):
            value = line.replace("VOCATIONAL_AREAS:", "").strip().lower()
            if value and value != "none" and value != "none identified":
                vocational_areas = [x.strip() for x in value.split(",") if x.strip()]
        
        elif line.startswith("SEND_NEEDS:"):
            value = line.replace("SEND_NEEDS:", "").strip().lower()
            if value and value != "none" and value != "none identified":
                send_needs = [x.strip() for x in value.split(",") if x.strip()]
        
        elif line.startswith("SUPPORT_NEEDS:"):
            value = line.replace("SUPPORT_NEEDS:", "").strip().lower()
            if value and value != "none" and value != "none identified":
                support_needs = [x.strip() for x in value.split(",") if x.strip()]
        
        elif line.startswith("CONFIDENCE:"):
            value = line.replace("CONFIDENCE:", "").strip()
            try:
                confidence = float(value)
                confidence = max(0.0, min(1.0, confidence))
            except:
                confidence = 0.8
        
        elif line.startswith("NOTES:"):
            notes = line.replace("NOTES:", "").strip()
    
    # Remove duplicates
    target_settings = list(dict.fromkeys(target_settings))
    
    return ExtractedIntent(
        target_settings=target_settings,
        residential=residential,
        vocational_areas=vocational_areas,
        send_needs=send_needs,
        support_needs=support_needs,
        support_needs_free_text=original_prompt,
        confidence=confidence,
        notes=notes,
        original_prompt=original_prompt
    )


def _extract_with_keywords(prompt: str) -> ExtractedIntent:
    """
    Deterministic keyword-based extraction as fallback.
    
    Uses pattern matching to extract intent when LLM is not available.
    """
    prompt_lower = prompt.lower()
    
    # Default to FE colleges and training providers
    target_settings = [TargetSetting.FE_COLLEGE, TargetSetting.TRAINING_PROVIDER]
    
    # Check for explicit school/sixth form mentions
    if re.search(r'\b(school|secondary school)\b', prompt_lower) and not re.search(r'\b(college|post.?16)\b', prompt_lower):
        target_settings = [TargetSetting.SCHOOL]
    elif re.search(r'\b(sixth form|6th form)\b', prompt_lower):
        target_settings = [TargetSetting.SIXTH_FORM]
    
    # Detect residential preference
    residential = ResidentialPreference.ANY
    if re.search(r'\b(only residential|must be residential|residential only|need residential)\b', prompt_lower):
        residential = ResidentialPreference.MUST
    elif re.search(r'\b(residential college|residential provider|prefer residential|want residential)\b', prompt_lower):
        residential = ResidentialPreference.PREFER
    elif re.search(r'\b(no residential|not residential|exclude residential|local only)\b', prompt_lower):
        residential = ResidentialPreference.EXCLUDE
    elif re.search(r'\bresidential\b', prompt_lower):
        residential = ResidentialPreference.PREFER  # Mention implies preference
    
    # Extract vocational areas
    vocational_areas = []
    for area, keywords in VOCATIONAL_TAXONOMY.items():
        for keyword in keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', prompt_lower):
                vocational_areas.append(area)
                break  # Only add once per area
    
    # Extract SEND needs
    send_needs = []
    for need, keywords in SEND_KEYWORDS.items():
        for keyword in keywords:
            if re.search(rf'\b{re.escape(keyword)}\b', prompt_lower):
                send_needs.append(need)
                break
    
    # Extract support needs
    support_needs = []
    for support, keywords in SUPPORT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in prompt_lower:
                support_needs.append(support)
                break
    
    # Remove duplicates while preserving order
    vocational_areas = list(dict.fromkeys(vocational_areas))
    send_needs = list(dict.fromkeys(send_needs))
    support_needs = list(dict.fromkeys(support_needs))
    
    confidence = 0.7 if (vocational_areas or send_needs or support_needs) else 0.5
    notes = "Extracted using keyword rules (LLM not available)"
    
    return ExtractedIntent(
        target_settings=target_settings,
        residential=residential,
        vocational_areas=vocational_areas,
        send_needs=send_needs,
        support_needs=support_needs,
        support_needs_free_text=prompt,
        confidence=confidence,
        notes=notes,
        original_prompt=prompt
    )
