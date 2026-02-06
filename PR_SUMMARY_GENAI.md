# Pull Request Summary: GenAI-Driven Provider Matching

## What This PR Does

Implements intelligent, GenAI-powered provider matching that understands natural language queries like "I want to do catering at a residential college" and returns ranked results with transparent explanations.

## Key Features

### 🧠 Intent Extraction
- Extracts structured intent from natural language prompts
- Uses OpenAI/CrewAI with keyword fallback
- Detects: residential requirements, vocational interests, SEND needs, target provider types

### 🎯 Smart Filtering
- **Excludes schools by default** (targets FE colleges and training providers)
- Respects residential requirements (must/prefer/exclude)
- Infers provider types from names (handles missing data gracefully)

### 📊 Intent-Based Scoring
- Multi-factor ranking algorithm:
  - Distance (normalized by radius)
  - Residential match (-0.5 to +0.3)
  - Vocational alignment (up to +0.3)
  - SEND support (+0.4 for S41, +0.3 for specialist)
- Generates transparent match explanations

### ✅ Production Ready
- 12/12 unit tests passing
- 0 security vulnerabilities (CodeQL)
- Backwards compatible (prompt is optional)
- Graceful degradation (works without API key)
- Comprehensive documentation

## Example

**Input:**
```
GET /instant?prompt=I want to do catering at a residential college&postcode=LS1 1AA
```

**Output:**
```json
{
  "meta": {
    "extracted_intent": {
      "residential": "prefer",
      "vocational_areas": ["hospitality_catering"],
      "target_settings": ["fe_college", "training_provider"]
    }
  },
  "instant_dossiers": [
    {
      "score": 0.85,
      "match_reasons": [
        "Located 12.5 miles from your location",
        "✓ Residential provision available (preferred)",
        "✓ May offer courses in: Hospitality & Catering",
        "✓ Section 41 approved for SEND provision",
        "Type: FE College"
      ]
    }
  ]
}
```

## Files Changed

**New:**
- `tools/intent_model.py` - Intent data models
- `tools/intent_extractor.py` - LLM/keyword extraction
- `tools/provider_type_detector.py` - Type inference
- `test_intent_matching.py` - Test suite
- `GENAI_IMPLEMENTATION.md` - Implementation guide

**Modified:**
- `tools/scoring.py` - Added intent-based scoring
- `api/main.py` - Integrated intent extraction
- `tools/provider_repository.py` - Enhanced queries
- `README.md` - Comprehensive docs
- `.env.example` - CORS config

## Testing

✅ All 12 unit tests passing
✅ Provider type detection validated with real DB
✅ CodeQL security scan clean
✅ Backwards compatibility verified

## Configuration

**Required:**
- `USER_POSTCODE` - Default postcode

**Optional:**
- `OPENAI_API_KEY` - For LLM extraction
- `OPENAI_MODEL` - Model selection
- `CORS_ORIGINS` - Frontend origins

## Deployment

```bash
pip install -r requirements.txt
# Set OPENAI_API_KEY in .env
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Acceptance Criteria ✅

- [x] Prompt "catering at a residential college" works as expected
- [x] Schools excluded by default
- [x] Flexible CORS (no hardcoded ports)
- [x] Match reasons provide transparency
- [x] Works with/without LLM
- [x] Tests pass
- [x] Security scan clean
- [x] Documentation complete

## Code Review

✅ 2 issues identified and fixed:
- Fixed enum comparison (use direct comparison, not `.value`)
- Clarified sixth form college categorization

## Security

✅ **0 vulnerabilities** found by CodeQL

---

**Ready to merge** - All acceptance criteria met, tests passing, security clean, well documented.
