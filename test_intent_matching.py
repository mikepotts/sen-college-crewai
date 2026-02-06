#!/usr/bin/env python3
"""
Tests for Intent Extraction and Provider Matching.

Tests cover:
1. Intent extraction fallback rules
2. Provider type classification
3. Residential matching and ranking
4. School exclusion filtering
5. Integration scenarios
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_intent_extraction_fallback():
    """Test rule-based intent extraction when LLM is unavailable."""
    print("\n=== Test 1: Intent Extraction Fallback Rules ===")
    
    from tools.intent_extractor import _extract_with_rules
    
    # Test case 1: Residential + Catering
    prompt1 = "I want to do catering at a residential college"
    intent1 = _extract_with_rules(prompt1)
    
    print(f"Prompt: '{prompt1}'")
    print(f"  Residential: {intent1['residential']}")
    print(f"  Vocational areas: {intent1['vocational_areas']}")
    print(f"  Target settings: {intent1['target_settings']}")
    
    assert intent1['residential'] in ['must', 'prefer'], "Should detect residential preference"
    assert 'hospitality' in intent1['vocational_areas'], "Should detect hospitality/catering"
    assert 'SCHOOL' not in intent1['target_settings'], "Should not include schools by default"
    print("✓ Test 1.1 passed")
    
    # Test case 2: SEND needs detection
    prompt2 = "My child has autism and ADHD, needs quiet spaces and visual schedules"
    intent2 = _extract_with_rules(prompt2)
    
    print(f"\nPrompt: '{prompt2}'")
    print(f"  SEND needs: {intent2['send_needs']}")
    
    assert 'autism' in intent2['send_needs'], "Should detect autism"
    assert 'adhd' in intent2['send_needs'], "Should detect ADHD"
    assert 'sensory' in intent2['send_needs'], "Should detect sensory needs (quiet)"
    print("✓ Test 1.2 passed")
    
    # Test case 3: School inclusion when explicitly mentioned
    prompt3 = "Looking for a sixth form or school with IT courses"
    intent3 = _extract_with_rules(prompt3)
    
    print(f"\nPrompt: '{prompt3}'")
    print(f"  Target settings: {intent3['target_settings']}")
    
    assert 'SCHOOL' in intent3['target_settings'], "Should include schools when mentioned"
    print("✓ Test 1.3 passed")
    
    # Test case 4: Exclude residential
    prompt4 = "Looking for day provision only, no residential"
    intent4 = _extract_with_rules(prompt4)
    
    print(f"\nPrompt: '{prompt4}'")
    print(f"  Residential: {intent4['residential']}")
    
    assert intent4['residential'] == 'exclude', "Should exclude residential"
    print("✓ Test 1.4 passed")
    
    print("\nStatus: PASS - All fallback rules working correctly\n")


def test_provider_classification():
    """Test provider type classification from names."""
    print("\n=== Test 2: Provider Type Classification ===")
    
    from tools.provider_classifier import classify_provider, should_include_provider
    
    # Test FE colleges
    fe_providers = [
        {"name": "BARKING AND DAGENHAM COLLEGE"},
        {"name": "BARNSLEY COLLEGE"},
        {"name": "BASINGSTOKE COLLEGE OF TECHNOLOGY"},
    ]
    
    for provider in fe_providers:
        provider_type = classify_provider(provider)
        print(f"  '{provider['name']}' -> {provider_type}")
        assert provider_type in ["FE_COLLEGE", "SIXTH_FORM_COLLEGE"], f"Should classify as college: {provider['name']}"
    print("✓ FE colleges classified correctly")
    
    # Test schools
    schools = [
        {"name": "THE CAMDEN SCHOOL FOR GIRLS"},
        {"name": "ABBOT BEYNE SCHOOL"},
        {"name": "ACLAND BURGHLEY SCHOOL"},
    ]
    
    for provider in schools:
        provider_type = classify_provider(provider)
        print(f"  '{provider['name']}' -> {provider_type}")
        assert provider_type == "SCHOOL", f"Should classify as school: {provider['name']}"
    print("✓ Schools classified correctly")
    
    # Test training providers
    training_providers = [
        {"name": "ACHIEVEMENT TRAINING LIMITED"},
        {"name": "ACORN TRAINING CONSULTANTS LIMITED"},
        {"name": "5 E LTD."},
    ]
    
    for provider in training_providers:
        provider_type = classify_provider(provider)
        print(f"  '{provider['name']}' -> {provider_type}")
        assert provider_type in ["TRAINING_PROVIDER", "UNKNOWN"], f"Should classify as training or unknown: {provider['name']}"
    print("✓ Training providers classified correctly")
    
    # Test sixth form colleges (specific case)
    sixth_form = {"name": "BARTON PEVERIL SIXTH FORM COLLEGE"}
    provider_type = classify_provider(sixth_form)
    print(f"  '{sixth_form['name']}' -> {provider_type}")
    assert provider_type == "SIXTH_FORM_COLLEGE", "Should classify as sixth form college"
    print("✓ Sixth form college classified correctly")
    
    print("\nStatus: PASS - Provider classification working\n")


def test_school_exclusion():
    """Test that schools are excluded by default."""
    print("\n=== Test 3: School Exclusion Filter ===")
    
    from tools.provider_classifier import should_include_provider
    
    # Default target settings (FE + Training, no schools)
    default_target = ["FE_COLLEGE", "TRAINING_PROVIDER"]
    
    # Should include
    college = {"name": "BARNSLEY COLLEGE"}
    training = {"name": "ACHIEVEMENT TRAINING LIMITED"}
    sixth_form = {"name": "BARTON PEVERIL SIXTH FORM COLLEGE"}
    
    assert should_include_provider(college, default_target), "Should include FE college"
    assert should_include_provider(training, default_target), "Should include training provider"
    assert should_include_provider(sixth_form, default_target), "Should include sixth form college"
    print("✓ FE colleges and training providers included")
    
    # Should exclude
    school = {"name": "THE CAMDEN SCHOOL FOR GIRLS"}
    assert not should_include_provider(school, default_target), "Should exclude school"
    print("✓ Schools excluded by default")
    
    # When schools are included in target
    school_target = ["FE_COLLEGE", "TRAINING_PROVIDER", "SCHOOL"]
    assert should_include_provider(school, school_target), "Should include school when in target"
    print("✓ Schools included when explicitly requested")
    
    print("\nStatus: PASS - School exclusion working correctly\n")


def test_residential_scoring():
    """Test residential matching and scoring."""
    print("\n=== Test 4: Residential Matching and Scoring ===")
    
    from tools.intent_matching import score_provider_with_intent, filter_providers_by_residential
    
    # Test filtering with "must" preference
    providers = [
        {"provider_id": "1", "name": "Non-Residential College", "is_residential": 0},
        {"provider_id": "2", "name": "Residential College", "is_residential": 1},
    ]
    
    intent_must = {"residential": "must"}
    filtered_must = filter_providers_by_residential(providers, "must")
    
    print(f"Residential 'must' filter:")
    print(f"  Original count: {len(providers)}")
    print(f"  Filtered count: {len(filtered_must)}")
    assert len(filtered_must) == 1, "Should only include residential providers"
    assert filtered_must[0]["is_residential"] == 1, "Should be residential provider"
    print("✓ 'Must' filtering works")
    
    # Test filtering with "exclude" preference
    filtered_exclude = filter_providers_by_residential(providers, "exclude")
    
    print(f"\nResidential 'exclude' filter:")
    print(f"  Filtered count: {len(filtered_exclude)}")
    assert len(filtered_exclude) == 1, "Should only include non-residential providers"
    assert filtered_exclude[0]["is_residential"] == 0, "Should be non-residential provider"
    print("✓ 'Exclude' filtering works")
    
    # Test scoring boost
    provider_residential = {
        "provider_id": "2",
        "name": "Residential College",
        "is_residential": 1,
        "is_specialist": 0,
        "s41_approved": 0
    }
    
    intent_prefer = {
        "residential": "prefer",
        "vocational_areas": [],
        "send_needs": []
    }
    
    base_score = 0.5
    score, reasons = score_provider_with_intent(
        provider_residential, intent_prefer, base_score, 10.0, 50.0
    )
    
    print(f"\nScoring residential provider with 'prefer' intent:")
    print(f"  Base score: {base_score}")
    print(f"  Final score: {score}")
    print(f"  Boost: {score - base_score}")
    print(f"  Reasons: {reasons}")
    
    assert score > base_score, "Residential provider should get boost when preferred"
    assert any("residential" in r.lower() for r in reasons), "Should mention residential in reasons"
    print("✓ Residential scoring boost works")
    
    print("\nStatus: PASS - Residential matching working correctly\n")


def test_send_needs_scoring():
    """Test SEND needs matching and scoring."""
    print("\n=== Test 5: SEND Needs Scoring ===")
    
    from tools.intent_matching import score_provider_with_intent
    
    # Specialist provider with S41
    specialist_provider = {
        "provider_id": "S1",
        "name": "Specialist SEND College",
        "is_residential": 0,
        "is_specialist": 1,
        "s41_approved": 1
    }
    
    intent_send = {
        "residential": "any",
        "vocational_areas": [],
        "send_needs": ["autism", "adhd"]
    }
    
    base_score = 0.5
    score, reasons = score_provider_with_intent(
        specialist_provider, intent_send, base_score, 10.0, 50.0
    )
    
    print(f"Specialist provider with SEND needs:")
    print(f"  Base score: {base_score}")
    print(f"  Final score: {score}")
    print(f"  Boost: {score - base_score}")
    print(f"  Reasons: {reasons}")
    
    assert score > base_score, "Specialist provider should get boost for SEND needs"
    assert any("s41" in r.lower() or "section 41" in r.lower() for r in reasons), "Should mention S41"
    assert any("specialist" in r.lower() for r in reasons), "Should mention specialist"
    print("✓ SEND needs scoring boost works")
    
    print("\nStatus: PASS - SEND needs scoring working correctly\n")


def test_vocational_matching():
    """Test vocational area matching."""
    print("\n=== Test 6: Vocational Area Matching ===")
    
    from tools.intent_matching import score_provider_with_intent
    
    # Provider with hospitality keywords in name
    hospitality_provider = {
        "provider_id": "H1",
        "name": "College of Hospitality and Catering",
        "is_residential": 0,
        "is_specialist": 0,
        "s41_approved": 0,
        "website": "http://example.com/hospitality"
    }
    
    intent_hospitality = {
        "residential": "any",
        "vocational_areas": ["hospitality"],
        "send_needs": []
    }
    
    base_score = 0.5
    score, reasons = score_provider_with_intent(
        hospitality_provider, intent_hospitality, base_score, 10.0, 50.0
    )
    
    print(f"Hospitality provider with hospitality intent:")
    print(f"  Base score: {base_score}")
    print(f"  Final score: {score}")
    print(f"  Boost: {score - base_score}")
    print(f"  Reasons: {reasons}")
    
    assert score > base_score, "Provider with matching vocational area should get boost"
    assert any("hospitality" in r.lower() for r in reasons), "Should mention hospitality in reasons"
    print("✓ Vocational matching boost works")
    
    print("\nStatus: PASS - Vocational matching working correctly\n")


def test_integration_scenario():
    """Test complete integration scenario: 'I want to do catering at a residential college'."""
    print("\n=== Test 7: Integration Scenario ===")
    
    from tools.intent_extractor import _extract_with_rules
    from tools.provider_classifier import should_include_provider
    from tools.intent_matching import score_provider_with_intent, filter_providers_by_residential
    
    prompt = "I want to do catering at a residential college"
    print(f"User prompt: '{prompt}'")
    
    # Step 1: Extract intent
    intent = _extract_with_rules(prompt)
    print(f"\nExtracted intent:")
    print(f"  Residential: {intent['residential']}")
    print(f"  Vocational areas: {intent['vocational_areas']}")
    print(f"  Target settings: {intent['target_settings']}")
    print(f"  Confidence: {intent['confidence']}")
    
    assert 'hospitality' in intent['vocational_areas'], "Should detect catering/hospitality"
    assert intent['residential'] in ['must', 'prefer'], "Should detect residential preference"
    
    # Step 2: Create sample providers
    providers = [
        {
            "provider_id": "1",
            "name": "THE CAMDEN SCHOOL FOR GIRLS",
            "is_residential": 0,
            "is_specialist": 0,
            "s41_approved": 0
        },
        {
            "provider_id": "2",
            "name": "BARNSLEY COLLEGE",
            "is_residential": 0,
            "is_specialist": 0,
            "s41_approved": 0
        },
        {
            "provider_id": "3",
            "name": "RESIDENTIAL HOSPITALITY COLLEGE",
            "is_residential": 1,
            "is_specialist": 0,
            "s41_approved": 0,
            "website": "http://example.com/hospitality"
        },
        {
            "provider_id": "4",
            "name": "SPECIALIST RESIDENTIAL COLLEGE",
            "is_residential": 1,
            "is_specialist": 1,
            "s41_approved": 1
        },
    ]
    
    # Step 3: Filter by provider type (exclude schools)
    target_settings = intent['target_settings']
    filtered_by_type = [p for p in providers if should_include_provider(p, target_settings)]
    
    print(f"\nAfter provider type filtering:")
    print(f"  Original: {len(providers)} providers")
    print(f"  Filtered: {len(filtered_by_type)} providers")
    for p in filtered_by_type:
        print(f"    - {p['name']}")
    
    assert len(filtered_by_type) == 3, "Should exclude school"
    assert not any("SCHOOL FOR GIRLS" in p["name"] for p in filtered_by_type), "School should be excluded"
    
    # Step 4: Apply residential filtering
    residential_pref = intent['residential']
    if residential_pref == 'must':
        filtered_residential = filter_providers_by_residential(filtered_by_type, residential_pref)
        print(f"\nAfter residential 'must' filtering:")
        print(f"  Filtered: {len(filtered_residential)} providers")
        for p in filtered_residential:
            print(f"    - {p['name']}")
        assert all(p['is_residential'] for p in filtered_residential), "All should be residential"
        filtered_by_type = filtered_residential
    
    # Step 5: Score providers
    scored = []
    for provider in filtered_by_type:
        base_score = 0.5
        score, reasons = score_provider_with_intent(
            provider, intent, base_score, 10.0, 50.0
        )
        scored.append({
            "provider": provider,
            "score": score,
            "reasons": reasons
        })
    
    # Sort by score
    scored.sort(key=lambda x: -x["score"])
    
    print(f"\nTop providers after scoring:")
    for i, item in enumerate(scored[:3], 1):
        print(f"  {i}. {item['provider']['name']} (score: {item['score']:.2f})")
        print(f"     Reasons: {item['reasons'][:2]}")
    
    # Verify residential + hospitality provider is ranked highly
    top_provider = scored[0]['provider']
    assert top_provider['is_residential'], "Top provider should be residential"
    print("\n✓ Residential providers ranked higher (as expected)")
    
    # Check if hospitality college is at/near top
    hospitality_rank = next(
        (i for i, item in enumerate(scored) if 'HOSPITALITY' in item['provider']['name']),
        None
    )
    if hospitality_rank is not None:
        print(f"✓ Hospitality college ranked at position {hospitality_rank + 1}")
    
    print("\nStatus: PASS - Integration scenario working correctly\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Intent Extraction and Provider Matching Tests")
    print("=" * 70)
    
    try:
        test_intent_extraction_fallback()
        test_provider_classification()
        test_school_exclusion()
        test_residential_scoring()
        test_send_needs_scoring()
        test_vocational_matching()
        test_integration_scenario()
        
        print("=" * 70)
        print("All tests completed successfully! ✓")
        print("=" * 70)
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
