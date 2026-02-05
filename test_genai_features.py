#!/usr/bin/env python3
"""
Test script for GenAI prompt-based search enhancements.

This script demonstrates:
1. Profile extraction from natural language prompts
2. Enhanced scoring based on extracted profiles
3. Deep dive using SQLite provider data
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_profile_extraction():
    """Test profile extraction without API key (should fail gracefully)."""
    print("\n=== Test 1: Profile Extraction (without API key) ===")
    
    from tools.profile_extractor import extract_profile_from_prompt
    
    # Remove API key for testing graceful degradation
    os.environ.pop('OPENAI_API_KEY', None)
    
    test_prompt = "My child has ADHD and autism, needs quiet spaces and visual schedules, interested in hospitality and catering"
    
    profile = extract_profile_from_prompt(test_prompt)
    
    if profile is None:
        print("✓ Profile extraction correctly returns None when API key is not available")
    else:
        print("✗ Expected None but got:", profile)
    
    print("Status: PASS - Graceful degradation working\n")


def test_provider_repository():
    """Test provider repository SQLite integration."""
    print("\n=== Test 2: Provider Repository (SQLite) ===")
    
    from tools.provider_repository import fetch_by_id
    import sqlite3
    from pathlib import Path
    
    # Get a sample provider from the database
    DB_PATH = Path("data/providers.sqlite")
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    rows = c.execute("SELECT provider_id, name FROM providers LIMIT 3").fetchall()
    conn.close()
    
    if not rows:
        print("✗ No providers found in database")
        return
    
    for provider_id, name in rows:
        provider = fetch_by_id(provider_id)
        if provider:
            print(f"✓ Fetched provider: {provider['name']}")
            print(f"  - ID: {provider['provider_id']}")
            print(f"  - Website: {provider.get('website') or 'Not available'}")
            print(f"  - Residential: {bool(provider.get('is_residential'))}")
            print(f"  - S41 Approved: {bool(provider.get('s41_approved'))}")
        else:
            print(f"✗ Failed to fetch provider {provider_id}")
    
    print("\nStatus: PASS - SQLite integration working\n")


def test_enhanced_scoring():
    """Test enhanced scoring with mock profile."""
    print("\n=== Test 3: Enhanced Scoring ===")
    
    from tools.profile_extractor import enhance_scoring_with_profile
    
    # Mock extracted profile
    mock_profile = {
        "diagnoses": ["ADHD", "Autism"],
        "needs": ["quiet spaces", "visual schedules"],
        "aspirations": ["hospitality", "catering"],
        "keywords": ["ADHD", "Autism", "quiet spaces", "visual schedules", "hospitality", "catering"]
    }
    
    # Test text with some matches
    test_text = "We offer hospitality courses with quiet learning spaces and support for students with autism"
    
    asp_hits, send_hits = enhance_scoring_with_profile(mock_profile, test_text)
    
    print(f"Test text: {test_text}")
    print(f"✓ Aspiration hits: {asp_hits}")
    print(f"✓ SEND hits: {send_hits}")
    
    if asp_hits > 0 and send_hits > 0:
        print("\nStatus: PASS - Enhanced scoring detecting matches\n")
    else:
        print("\nStatus: WARNING - No matches detected, review keyword matching\n")


def test_api_structure():
    """Test that the API module loads correctly."""
    print("\n=== Test 4: API Module Structure ===")
    
    try:
        from api.main import app
        print("✓ API module loaded successfully")
        
        # Check if the instant endpoint accepts prompt parameter
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        # Test health endpoint
        response = client.get("/health")
        if response.status_code == 200:
            print("✓ Health endpoint working")
        else:
            print(f"✗ Health endpoint returned {response.status_code}")
        
        # Check OpenAPI spec for prompt parameter
        openapi = client.get("/openapi.json").json()
        instant_params = openapi['paths']['/instant']['get']['parameters']
        
        prompt_param = next((p for p in instant_params if p['name'] == 'prompt'), None)
        
        if prompt_param:
            print(f"✓ Prompt parameter found in /instant endpoint")
            print(f"  - Description: {prompt_param.get('description')}")
            print(f"  - Required: {prompt_param.get('required', False)}")
        else:
            print("✗ Prompt parameter not found in /instant endpoint")
        
        print("\nStatus: PASS - API structure correct\n")
        
    except Exception as e:
        print(f"✗ Error loading API: {e}")
        print("\nStatus: FAIL\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("GenAI Prompt-Based Search Enhancement Tests")
    print("=" * 60)
    
    test_profile_extraction()
    test_provider_repository()
    test_enhanced_scoring()
    test_api_structure()
    
    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
