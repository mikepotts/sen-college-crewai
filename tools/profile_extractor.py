"""
Profile Extractor using CrewAI to parse natural language prompts into structured child profiles.

This module uses a CrewAI agent to extract structured information from free-text user descriptions
about a child's needs, diagnoses, aspirations, and preferences.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from crewai import Agent, Task, Crew, Process, LLM

logger = logging.getLogger(__name__)


def extract_profile_from_prompt(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Use CrewAI to extract a structured profile from a natural language prompt.
    
    Args:
        prompt: Free-text description of child needs, diagnoses, aspirations, and preferences
        
    Returns:
        Dictionary with extracted profile containing:
        - diagnoses: List[str] - identified diagnoses/conditions
        - needs: List[str] - identified needs and support requirements
        - aspirations: List[str] - career/course aspirations
        - keywords: List[str] - all relevant keywords for search enhancement
        - summary: str - brief summary of the profile
        
        Returns None if extraction fails or API key is not available
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, profile extraction disabled")
        return None
    
    try:
        # Initialize the LLM using CrewAI's LLM class
        llm = LLM(
            model=f"openai/{model_name}",
            api_key=api_key,
            temperature=0.3
        )
        
        # Define the extraction agent
        profile_agent = Agent(
            role="SEND Education Profile Analyst",
            goal="Extract structured information about a child's educational needs, diagnoses, and aspirations from natural language descriptions",
            backstory=(
                "You are an expert in Special Educational Needs and Disabilities (SEND) education. "
                "You understand how to identify diagnoses (like ADHD, Autism, Dyslexia), "
                "support needs (like reading support, quiet environments, visual schedules), "
                "and career aspirations (like hospitality, catering, IT) from parent or guardian descriptions."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False
        )
        
        # Define the extraction task
        extraction_task = Task(
            description=(
                f"Analyze this description of a child's needs and extract structured information:\n\n"
                f"{prompt}\n\n"
                f"Extract and categorize:\n"
                f"1. DIAGNOSES: Any mentioned conditions (ADHD, Autism, Dyslexia, etc.)\n"
                f"2. NEEDS: Support requirements (reading help, quiet spaces, visual aids, small groups, etc.)\n"
                f"3. ASPIRATIONS: Career interests or course preferences (hospitality, catering, IT, etc.)\n"
                f"4. KEYWORDS: All relevant terms that would help find suitable colleges\n"
                f"5. SUMMARY: A brief 1-2 sentence summary of the profile"
            ),
            expected_output=(
                "A structured response in this exact format:\n"
                "DIAGNOSES: comma-separated list or 'None identified'\n"
                "NEEDS: comma-separated list or 'None identified'\n"
                "ASPIRATIONS: comma-separated list or 'None identified'\n"
                "KEYWORDS: comma-separated list of all relevant search terms\n"
                "SUMMARY: Brief summary sentence"
            ),
            agent=profile_agent
        )
        
        # Create and run the crew
        crew = Crew(
            agents=[profile_agent],
            tasks=[extraction_task],
            process=Process.sequential,
            verbose=False
        )
        
        result = crew.kickoff()
        
        # Parse the result
        profile = _parse_extraction_result(str(result))
        
        logger.info(f"Profile extraction successful: {len(profile.get('keywords', []))} keywords extracted")
        return profile
        
    except Exception as e:
        logger.error(f"Profile extraction failed: {e}", exc_info=True)
        return None


def _parse_extraction_result(result: str) -> Dict[str, Any]:
    """Parse the CrewAI agent output into structured format."""
    lines = result.strip().split('\n')
    profile = {
        "diagnoses": [],
        "needs": [],
        "aspirations": [],
        "keywords": [],
        "summary": ""
    }
    
    for line in lines:
        line = line.strip()
        if line.startswith("DIAGNOSES:"):
            items = line.replace("DIAGNOSES:", "").strip()
            if items and items.lower() != "none identified":
                profile["diagnoses"] = [x.strip() for x in items.split(",") if x.strip()]
        elif line.startswith("NEEDS:"):
            items = line.replace("NEEDS:", "").strip()
            if items and items.lower() != "none identified":
                profile["needs"] = [x.strip() for x in items.split(",") if x.strip()]
        elif line.startswith("ASPIRATIONS:"):
            items = line.replace("ASPIRATIONS:", "").strip()
            if items and items.lower() != "none identified":
                profile["aspirations"] = [x.strip() for x in items.split(",") if x.strip()]
        elif line.startswith("KEYWORDS:"):
            items = line.replace("KEYWORDS:", "").strip()
            if items:
                profile["keywords"] = [x.strip() for x in items.split(",") if x.strip()]
        elif line.startswith("SUMMARY:"):
            profile["summary"] = line.replace("SUMMARY:", "").strip()
    
    # Combine all extracted items into keywords if not already present
    all_items = profile["diagnoses"] + profile["needs"] + profile["aspirations"]
    for item in all_items:
        if item and item not in profile["keywords"]:
            profile["keywords"].append(item)
    
    return profile


def enhance_scoring_with_profile(profile: Dict[str, Any], text: str) -> tuple[int, int]:
    """
    Calculate enhanced aspiration and SEND keyword hits based on extracted profile.
    
    Args:
        profile: Extracted profile dictionary with keywords
        text: Text to search for keywords (provider description, etc.)
        
    Returns:
        Tuple of (aspiration_hits, send_hits)
    """
    if not profile or not profile.get("keywords"):
        return 0, 0
    
    text_lower = text.lower()
    aspiration_hits = 0
    send_hits = 0
    
    # Count aspiration matches
    for asp in profile.get("aspirations", []):
        if asp.lower() in text_lower:
            aspiration_hits += 1
    
    # Count SEND/needs matches
    for need in profile.get("needs", []) + profile.get("diagnoses", []):
        if need.lower() in text_lower:
            send_hits += 1
    
    return aspiration_hits, send_hits
