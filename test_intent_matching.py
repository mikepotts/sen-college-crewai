"""
Tests for intent extraction and provider matching features.
"""

from tools.intent_model import ExtractedIntent, TargetSetting, ResidentialPreference
from tools.intent_extractor import _extract_with_keywords
from tools.provider_type_detector import infer_provider_type, matches_target_settings
from tools.scoring import intent_based_score
from config import ScoringConfig


def test_extract_residential_must():
    """Test extraction of 'must have residential' requirement."""
    prompt = "I need a residential college for my child"
    intent = _extract_with_keywords(prompt)
    
    assert intent.residential == ResidentialPreference.MUST, f"Expected MUST, got {intent.residential}"
    assert intent.original_prompt == prompt
    print("✓ test_extract_residential_must passed")


def test_extract_vocational_hospitality():
    """Test extraction of hospitality/catering interest."""
    prompt = "My child wants to do catering at a college"
    intent = _extract_with_keywords(prompt)
    
    assert "hospitality_catering" in intent.vocational_areas, f"hospitality_catering not found in {intent.vocational_areas}"
    print("✓ test_extract_vocational_hospitality passed")


def test_extract_send_needs_autism():
    """Test extraction of autism SEND need."""
    prompt = "My child has autism and needs support"
    intent = _extract_with_keywords(prompt)
    
    assert "autism" in intent.send_needs, f"autism not found in {intent.send_needs}"
    print("✓ test_extract_send_needs_autism passed")


def test_default_target_settings():
    """Test that default target settings are FE colleges and training providers."""
    prompt = "Looking for a post-16 provider"
    intent = _extract_with_keywords(prompt)
    
    assert TargetSetting.FE_COLLEGE in intent.target_settings
    assert TargetSetting.TRAINING_PROVIDER in intent.target_settings
    assert TargetSetting.SCHOOL not in intent.target_settings
    print("✓ test_default_target_settings passed")


def test_complex_prompt():
    """Test extraction from a complex real-world prompt."""
    prompt = "I want to do catering at a residential college. My child has ADHD and needs quiet spaces and visual schedules"
    intent = _extract_with_keywords(prompt)
    
    assert intent.residential == ResidentialPreference.PREFER, f"Expected PREFER, got {intent.residential}"
    assert "hospitality_catering" in intent.vocational_areas, f"hospitality_catering not found"
    assert "adhd" in intent.send_needs, f"adhd not found in {intent.send_needs}"
    assert "quiet_spaces" in intent.support_needs, f"quiet_spaces not found"
    print("✓ test_complex_prompt passed")


def test_detect_fe_college():
    """Test detection of FE college from name."""
    provider = {"name": "Leeds City College", "provider_type": None}
    ptype = infer_provider_type(provider)
    
    assert ptype == "FE_COLLEGE", f"Expected FE_COLLEGE, got {ptype}"
    print("✓ test_detect_fe_college passed")


def test_detect_training_provider():
    """Test detection of training provider from name."""
    provider = {"name": "ABC Training Limited", "provider_type": None}
    ptype = infer_provider_type(provider)
    
    assert ptype == "TRAINING_PROVIDER", f"Expected TRAINING_PROVIDER, got {ptype}"
    print("✓ test_detect_training_provider passed")


def test_detect_school():
    """Test detection of school from name."""
    provider = {"name": "Example Academy School", "provider_type": None}
    ptype = infer_provider_type(provider)
    
    assert ptype == "SCHOOL", f"Expected SCHOOL, got {ptype}"
    print("✓ test_detect_school passed")


def test_excludes_school_by_default():
    """Test that schools are excluded when targeting FE/training."""
    provider = {"name": "Example School", "provider_type": None}
    target_settings = [TargetSetting.FE_COLLEGE, TargetSetting.TRAINING_PROVIDER]
    
    result = matches_target_settings(provider, target_settings)
    assert result is False, f"School should be excluded but got {result}"
    print("✓ test_excludes_school_by_default passed")


def test_residential_boost_when_matched():
    """Test that residential providers get a boost when residential is preferred."""
    provider = {
        "name": "Example College",
        "is_residential": 1,
        "is_specialist": 0,
        "s41_approved": 0,
        "provider_type": None,
        "website": ""
    }
    
    intent = ExtractedIntent(
        residential=ResidentialPreference.PREFER,
        original_prompt="prefer residential"
    )
    
    cfg = ScoringConfig()
    score, breakdown, reasons = intent_based_score(
        provider, distance_miles=10.0, radius_miles=50.0, intent=intent, cfg=cfg
    )
    
    assert breakdown.get("residential_boost", 0) > 0, f"Expected positive boost, got {breakdown.get('residential_boost')}"
    assert any("residential" in r.lower() for r in reasons), f"No residential mention in {reasons}"
    print("✓ test_residential_boost_when_matched passed")


def test_send_boost_for_s41():
    """Test that S41 approved providers get SEND boost."""
    provider = {
        "name": "Example College",
        "is_residential": 0,
        "is_specialist": 0,
        "s41_approved": 1,
        "provider_type": None,
        "website": ""
    }
    
    intent = ExtractedIntent(
        send_needs=["autism"],
        original_prompt="child has autism"
    )
    
    cfg = ScoringConfig()
    score, breakdown, reasons = intent_based_score(
        provider, distance_miles=10.0, radius_miles=50.0, intent=intent, cfg=cfg
    )
    
    assert breakdown.get("send_component", 0) > 0, f"Expected positive SEND component"
    assert any("section 41" in r.lower() for r in reasons), f"No S41 mention in {reasons}"
    print("✓ test_send_boost_for_s41 passed")


def test_match_reasons_generated():
    """Test that match reasons are always generated."""
    provider = {
        "name": "Example College",
        "is_residential": 0,
        "is_specialist": 0,
        "s41_approved": 0,
        "provider_type": None,
        "website": ""
    }
    
    intent = ExtractedIntent(original_prompt="looking for college")
    cfg = ScoringConfig()
    
    _, _, reasons = intent_based_score(
        provider, distance_miles=10.0, radius_miles=50.0, intent=intent, cfg=cfg
    )
    
    assert len(reasons) > 0, "No match reasons generated"
    assert isinstance(reasons, list), f"Expected list, got {type(reasons)}"
    print("✓ test_match_reasons_generated passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Intent Extraction and Matching Tests")
    print("=" * 60)
    
    tests = [
        test_extract_residential_must,
        test_extract_vocational_hospitality,
        test_extract_send_needs_autism,
        test_default_target_settings,
        test_complex_prompt,
        test_detect_fe_college,
        test_detect_training_provider,
        test_detect_school,
        test_excludes_school_by_default,
        test_residential_boost_when_matched,
        test_send_boost_for_s41,
        test_match_reasons_generated,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} error: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Tests: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
