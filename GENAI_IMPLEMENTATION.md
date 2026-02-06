# GenAI Provider Matching - Implementation Summary

## Overview

This implementation adds GenAI-driven intent extraction and intelligent provider matching to the SEN College Finder API. The system understands natural language queries and ranks providers based on residential preferences, vocational interests, and SEND support needs.

## What Was Changed

### New Files Created

1. **tools/intent_model.py** (165 lines)
   - Pydantic models for structured intent
   - Enums: `TargetSetting` (FE_COLLEGE, TRAINING_PROVIDER, SIXTH_FORM, SCHOOL, ANY)
   - Enums: `ResidentialPreference` (MUST, PREFER, EXCLUDE, ANY)
   - Vocational taxonomy with 10 career areas
   - SEND and support keywords library

2. **tools/intent_extractor.py** (293 lines)
   - LLM-based intent extraction using CrewAI/OpenAI
   - Deterministic keyword fallback when LLM unavailable
   - Extracts: target settings, residential preference, vocational areas, SEND needs
   - Returns confidence score and extraction notes

3. **tools/provider_type_detector.py** (171 lines)
   - Infers provider types from name patterns
   - Detects: FE colleges, training providers, schools, sixth forms
   - Filters providers by target settings
   - Returns human-readable type labels

4. **test_intent_matching.py** (234 lines)
   - Comprehensive test suite (12 tests, all passing)
   - Tests intent extraction, provider type detection, scoring
   - Validates residential, vocational, and SEND matching

### Files Modified

1. **tools/scoring.py** (+156 lines)
   - New `intent_based_score()` function
   - Multi-factor scoring:
     - Distance component (normalized by radius)
     - Residential boost: +0.15 (prefer) to -0.5 (missing must-have)
     - Vocational match: up to +0.3 for multiple matches
     - SEND support: +0.4 (S41), +0.3 (specialist)
   - Generates `match_reasons` array for transparency

2. **api/main.py** (+15 lines, modified scoring flow)
   - Replaced profile extraction with intent extraction
   - Added provider type filtering (excludes schools by default)
   - Added residential filtering based on intent
   - Integrated intent_based_score for ranking
   - Returns extracted_intent in meta response
   - Updated to use proper enum comparisons

3. **tools/provider_repository.py** (+3 fields)
   - Added `is_specialist` and `provider_type` to all queries
   - Ensures all provider data needed for scoring is fetched

4. **README.md** (completely rewritten, +180 lines)
   - Comprehensive feature documentation
   - Example queries and use cases
   - Scoring algorithm explanation
   - Response structure examples
   - Testing instructions

5. **.env.example** (+4 lines)
   - Added `CORS_ORIGINS` configuration
   - Documented flexible CORS setup

### Database Changes

**None required** - Works with existing schema. The implementation infers provider types from names since the `provider_type` column is currently NULL.

## How It Works

### 1. Intent Extraction Flow

```
User Prompt → LLM/Keywords → ExtractedIntent
                                ↓
                    (target_settings, residential,
                     vocational_areas, send_needs)
```

**Example:**
```
Input: "I want to do catering at a residential college"

Output:
- target_settings: [FE_COLLEGE, TRAINING_PROVIDER]
- residential: PREFER
- vocational_areas: ["hospitality_catering"]
- send_needs: []
```

### 2. Provider Filtering

Providers are filtered in two stages:

**Stage 1: Type Filtering**
```python
# Default behavior: exclude schools
if extracted_intent:
    keep = matches_target_settings(provider, intent.target_settings)
else:
    keep = (infer_provider_type(provider) != "SCHOOL")
```

**Stage 2: Residential Filtering**
```python
if intent.residential == MUST:
    # Only show residential
    providers = [p for p in pool if p.is_residential]
```

### 3. Scoring and Ranking

Providers are scored using a multi-factor algorithm:

```
Score = (w_distance × distance_comp) +
        (residential_boost) +
        (w_aspiration × vocational_comp) +
        (w_send × send_comp)

Where:
- distance_comp = 1 - (distance / radius)
- residential_boost = -0.5 to +0.3 based on match
- vocational_comp = 0 to 1 based on keyword matches
- send_comp = 0.1 to 0.8 based on S41/specialist flags
```

**Match Reasons Generated:**
- "Located X miles from your location"
- "✓ Residential provision available (preferred)"
- "✓ May offer courses in: Hospitality & Catering"
- "✓ Section 41 approved for SEND provision"
- "Type: FE College"

## Testing

### Unit Tests (12/12 passing)

**Intent Extraction:**
- ✓ Residential detection (must, prefer, exclude)
- ✓ Vocational area matching
- ✓ SEND needs extraction
- ✓ Default target settings

**Provider Type Detection:**
- ✓ FE college identification
- ✓ Training provider identification
- ✓ School identification and exclusion
- ✓ Sixth form distinction

**Scoring:**
- ✓ Residential boost when matched
- ✓ SEND boost for S41 approved
- ✓ Match reasons generation

### Database Testing

Tested with real database (1,941 providers):
- Sample of 100 providers: 33% FE colleges, 29% schools, 9% training, 25% unknown
- Filter to FE/training: 67% retained (schools excluded as expected)

### Security Testing

✅ **CodeQL scan: 0 vulnerabilities**

## Performance Considerations

### Optimizations:
- Intent extraction cached per request (not re-run for each provider)
- Provider type inference uses simple regex (fast)
- Scoring is O(n) where n = number of providers in radius
- Database query pulls all nearby providers once (avoids N+1)

### Known Limitations:
- Vocational matching is text-based (no course data in DB)
- Provider type inference from name only (not 100% accurate)
- No caching of intent extraction across requests

## Backwards Compatibility

✅ **Fully backwards compatible**

- `prompt` parameter is optional
- Without prompt, uses legacy scoring
- All existing parameters still work
- Response structure unchanged (only adds new fields)

## Configuration

### Required Environment Variables:
- `USER_POSTCODE` - Default postcode for searches
- `OPENAI_API_KEY` - For LLM intent extraction (optional, falls back to keywords)

### Optional Environment Variables:
- `OPENAI_MODEL` - LLM model selection (default: gpt-4o-mini)
- `CORS_ORIGINS` - Comma-separated allowed origins (defaults to localhost:5173,3000,5174)

## Example Usage

### Basic Search (No Prompt)
```bash
GET /instant?postcode=LS1%201AA&radius_miles=50&target_count=10
```
→ Legacy behavior, excludes schools by default

### With Prompt
```bash
GET /instant?postcode=LS1%201AA&radius_miles=50&target_count=10&prompt=I%20want%20to%20do%20catering%20at%20a%20residential%20college
```
→ Intent-based ranking with match explanations

### Response Structure
```json
{
  "meta": {
    "extracted_intent": {
      "target_settings": ["fe_college", "training_provider"],
      "residential": "prefer",
      "vocational_areas": ["hospitality_catering"],
      "confidence": 0.7
    }
  },
  "instant_dossiers": [
    {
      "provider": { "name": "...", "residential": true },
      "score": 0.85,
      "match_reasons": [
        "Located 12.5 miles from your location",
        "✓ Residential provision available (preferred)",
        "✓ May offer courses in: Hospitality & Catering",
        "Type: FE College"
      ]
    }
  ]
}
```

## Future Enhancements (Not in This PR)

1. **Course Data Integration**: Add actual course information to database for precise vocational matching
2. **Intent Caching**: Cache extracted intents to reduce API calls
3. **Provider Type Column**: Populate provider_type field in database
4. **ML-Based Matching**: Train model on successful placements
5. **User Feedback Loop**: Learn from user interactions to improve ranking

## Deployment Notes

### To Deploy:
1. `pip install -r requirements.txt` (includes crewai, openai)
2. Set `OPENAI_API_KEY` in environment
3. Restart API server
4. Test with: `curl http://localhost:8000/health`

### To Verify:
1. Check health endpoint returns 200
2. Test without prompt (should work as before)
3. Test with prompt (should return extracted_intent in meta)
4. Run tests: `python test_intent_matching.py`

## Acceptance Criteria - Status

✅ Prompt "I want to do catering at a residential college" produces results biased toward residential with hospitality/catering
✅ Default search excludes schools (verified with DB - 29% of providers are schools and are filtered)
✅ Works end-to-end with flexible port configuration (CORS_ORIGINS env var)
✅ LLM with graceful keyword fallback
✅ Unit tests added and passing (12/12)
✅ Code review completed and issues addressed
✅ Security scan clean (0 vulnerabilities)
✅ Comprehensive documentation

## Files Changed Summary

```
New Files:
+ tools/intent_model.py           (165 lines)
+ tools/intent_extractor.py       (293 lines)
+ tools/provider_type_detector.py (171 lines)
+ test_intent_matching.py         (234 lines)

Modified Files:
~ tools/scoring.py                (+156 lines)
~ api/main.py                     (+15 lines)
~ tools/provider_repository.py    (+3 fields)
~ README.md                       (rewritten, +180 lines)
~ .env.example                    (+4 lines)

Total: 4 new files, 5 modified files
Total Lines Added: ~1,000
```

## Contact

For questions about this implementation, please refer to:
- README.md - Full feature documentation
- test_intent_matching.py - Example usage
- tools/intent_model.py - Intent structure and taxonomy
