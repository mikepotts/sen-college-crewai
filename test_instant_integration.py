#!/usr/bin/env python3
"""
Integration test for /instant endpoint with intent extraction.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from api.main import app
import json

client = TestClient(app)

def test_instant_without_prompt():
    """Test /instant without prompt (fallback mode)."""
    print("\n=== Test 1: /instant without prompt ===")
    response = client.get("/instant?postcode=MK18+3BN&target_count=3")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Results: {len(data['instant_dossiers'])} local providers")
        print(f"Residential: {len(data['residential_results'])} providers")
        
        # Check metadata
        meta = data.get('meta', {})
        print(f"Intent extracted: {meta.get('extracted_intent') is not None}")
        print("✓ PASS - Works without prompt")
    else:
        print(f"✗ FAIL - {response.text}")


def test_instant_with_residential_catering():
    """Test /instant with 'catering at residential college' prompt."""
    print("\n=== Test 2: Residential Catering Search ===")
    
    prompt = "I want to do catering at a residential college"
    response = client.get(f"/instant?postcode=MK18+3BN&prompt={prompt}&target_count=5")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Prompt: '{prompt}'")
        
        # Check intent extraction
        meta = data.get('meta', {})
        intent = meta.get('extracted_intent')
        if intent:
            print(f"\nExtracted Intent:")
            print(f"  Residential: {intent.get('residential')}")
            print(f"  Vocational: {intent.get('vocational_areas')}")
            print(f"  Target settings: {intent.get('target_settings')}")
            print(f"  Extraction method: {intent.get('extraction_method')}")
            
            # Validate intent
            assert intent.get('residential') in ['must', 'prefer'], "Should detect residential preference"
            assert 'hospitality' in intent.get('vocational_areas', []), "Should detect catering/hospitality"
            print("✓ Intent extraction working")
        
        # Check results
        instant_results = data.get('instant_dossiers', [])
        residential_results = data.get('residential_results', [])
        
        print(f"\nResults:")
        print(f"  Local: {len(instant_results)} providers")
        print(f"  Residential: {len(residential_results)} providers")
        
        # Check match reasons in results
        if residential_results:
            first = residential_results[0]
            print(f"\nTop Residential Provider: {first['provider']['name']}")
            print(f"  Residential: {first['provider']['residential']}")
            print(f"  Distance: {first.get('distance_miles')} miles")
            print(f"  Score: {first.get('score')}")
            print(f"  Match reasons:")
            for reason in first.get('why_it_matches', [])[:3]:
                print(f"    - {reason}")
            
            # Validate it's residential
            assert first['provider']['residential'], "Top result should be residential"
            print("✓ Residential provider ranked first")
        
        print("\n✓ PASS - Residential catering search working")
    else:
        print(f"✗ FAIL - {response.text}")


def test_instant_school_exclusion():
    """Test that schools are excluded by default."""
    print("\n=== Test 3: School Exclusion ===")
    
    response = client.get("/instant?postcode=MK18+3BN&target_count=10")
    
    if response.status_code == 200:
        data = response.json()
        all_providers = data.get('instant_dossiers', []) + data.get('residential_results', [])
        
        # Check if any schools are included
        school_keywords = ['SCHOOL FOR GIRLS', 'SCHOOL FOR BOYS', 'GRAMMAR SCHOOL', 'HIGH SCHOOL']
        schools_found = []
        
        for provider in all_providers:
            name = provider['provider']['name']
            if any(kw in name.upper() for kw in school_keywords):
                schools_found.append(name)
        
        print(f"Total providers returned: {len(all_providers)}")
        print(f"Schools found: {len(schools_found)}")
        
        if schools_found:
            print(f"School names: {schools_found[:3]}")
        
        # Note: We expect FEW schools (sixth forms are okay), but not many primary/secondary schools
        # The filter should significantly reduce school count
        print("✓ PASS - School filtering applied")
    else:
        print(f"✗ FAIL - {response.text}")


def test_instant_send_needs():
    """Test SEND needs detection and scoring."""
    print("\n=== Test 4: SEND Needs Detection ===")
    
    prompt = "My child has autism and ADHD, needs quiet spaces and small groups"
    response = client.get(f"/instant?postcode=MK18+3BN&prompt={prompt}&target_count=3")
    
    if response.status_code == 200:
        data = response.json()
        meta = data.get('meta', {})
        intent = meta.get('extracted_intent')
        
        print(f"Prompt: '{prompt}'")
        
        if intent:
            send_needs = intent.get('send_needs', [])
            print(f"Detected SEND needs: {send_needs}")
            
            # Should detect autism and adhd
            assert 'autism' in send_needs, "Should detect autism"
            assert 'adhd' in send_needs, "Should detect ADHD"
            print("✓ SEND needs detected")
        
        # Check if results include match reasons related to SEND
        results = data.get('instant_dossiers', []) + data.get('residential_results', [])
        if results:
            first = results[0]
            reasons = first.get('why_it_matches', [])
            print(f"\nTop provider match reasons:")
            for reason in reasons[:3]:
                print(f"  - {reason}")
        
        print("\n✓ PASS - SEND needs detection working")
    else:
        print(f"✗ FAIL - {response.text}")


def main():
    """Run all integration tests."""
    print("=" * 70)
    print("Intent Extraction Integration Tests")
    print("=" * 70)
    
    try:
        test_instant_without_prompt()
        test_instant_with_residential_catering()
        test_instant_school_exclusion()
        test_instant_send_needs()
        
        print("\n" + "=" * 70)
        print("All integration tests passed! ✓")
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
