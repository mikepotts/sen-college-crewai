
# SEN College Finder – FastAPI Backend

## Overview

FastAPI backend for matching young people with SEND needs to appropriate post-16 education providers. Features GenAI-driven intent extraction to understand natural language search queries and intelligently rank providers based on residential preferences, vocational interests, and SEND support needs.

## Setup (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env   # set USER_POSTCODE, OPENAI_API_KEY, OPENAI_MODEL etc.
```

## Environment Variables

Required variables in `.env`:
- `USER_POSTCODE`: Default UK postcode for location-based searches (e.g., "LS1 1AA")
- `OPENAI_API_KEY`: OpenAI API key for GenAI prompt-based search features (optional but recommended)
- `OPENAI_MODEL`: OpenAI model to use (default: "gpt-4o-mini", alternative: "gpt-4")
- `CORS_ORIGINS`: Comma-separated list of allowed frontend origins (optional, defaults to common dev ports)

## Run the API
```powershell
powershell -ExecutionPolicy Bypass -File run_api.ps1
```
Open http://localhost:8000/docs

### Endpoints
- **GET /health** - Health check
- **GET /instant** - Fast search with intelligent matching
  - **Required**: `postcode` (UK postcode)
  - **Optional**: 
    - `radius_miles` - Search radius (default: expanding from 30 to 80 miles)
    - `target_count` - Number of results (default: 10)
    - `residential_mode` - Filter by residential provision (include/exclude/only)
    - `prompt` - Natural language description for GenAI-enhanced search ⭐ NEW
  - **Example**: `GET /instant?postcode=LS1%201AA&radius_miles=50&target_count=10&prompt=I%20want%20to%20do%20catering%20at%20a%20residential%20college`
- **POST /deep-dive** - Detailed provider analysis
  - Body: `{ "provider_id": "provider_123" }`

## GenAI Intent-Based Matching ⭐ NEW

The `/instant` endpoint now features intelligent intent extraction from natural language prompts. This provides a more intuitive search experience where users describe their needs in their own words.

### Features

#### 1. **Intent Extraction**
Automatically extracts structured information from free-text prompts:

- **Target Settings**: Infers whether user wants FE colleges, training providers, sixth forms, or schools
  - **Default**: FE colleges and training providers (excludes schools by default)
  - Keywords like "college", "training", "sixth form" adjust this
  
- **Residential Preference**: Detects residential requirements
  - `must` - Only show residential providers (e.g., "need residential", "only residential")
  - `prefer` - Boost residential providers (e.g., "prefer residential", "residential college")
  - `exclude` - Hide residential providers (e.g., "local only", "not residential")
  - `any` - No preference
  
- **Vocational Areas**: Identifies career interests from 10+ vocational categories
  - Hospitality & Catering (catering, cooking, chef, hospitality)
  - IT & Computing (IT, programming, coding, software)
  - Construction (building, carpentry, plumbing, electrical)
  - Creative Arts (art, design, media, music)
  - Health & Care (nursing, care, healthcare)
  - And more...
  
- **SEND Needs**: Recognizes diagnoses and support requirements
  - Diagnoses: autism, ADHD, dyslexia, dyspraxia, etc.
  - Support needs: quiet spaces, visual schedules, 1:1 support, etc.

#### 2. **Intelligent Scoring**
Providers are ranked using intent-aware scoring that considers:

- **Distance**: Closer providers score higher
- **Residential Match**: Strong boost/penalty based on requirement
  - MUST residential + non-residential provider = -0.5 penalty
  - PREFER residential + residential provider = +0.15 boost
- **Vocational Alignment**: Matches provider offerings to career interests
  - Text-based matching against provider name and website
  - Up to +0.3 boost for multiple vocational matches
- **SEND Support**: Prioritizes appropriate support levels
  - Section 41 approved providers: +0.4 boost
  - Specialist providers: +0.3 boost
  - All providers get baseline SEND score (assumes basic support)

#### 3. **Transparent Match Explanations**
Each result includes `match_reasons` explaining why it was selected:

- Distance information: "Located 12.5 miles from your location"
- Residential status: "✓ Residential provision available (preferred)"
- Vocational fit: "✓ May offer courses in: Hospitality & Catering"
- SEND support: "✓ Section 41 approved for SEND provision"
- Provider type: "Type: FE College"

#### 4. **Provider Type Filtering**
Intelligent provider type detection from name patterns:

- **Included by default**: FE colleges, training providers, unknown types (benefit of doubt)
- **Excluded by default**: Schools (unless explicitly mentioned in prompt)
- **Sixth forms**: Included when specifically requested

### Example Queries

**Example 1: Vocational Interest + Residential**
```
Prompt: "I want to do catering at a residential college"

Extracted Intent:
✓ Target: FE colleges, training providers
✓ Residential: prefer
✓ Vocational: hospitality_catering
✓ Schools excluded by default

Results ranked by:
- Proximity
- Residential provision (boosted)
- "catering" or "hospitality" in name/website
```

**Example 2: SEND Needs**
```
Prompt: "My child has autism and ADHD, needs quiet spaces and visual schedules"

Extracted Intent:
✓ SEND needs: autism, ADHD
✓ Support needs: quiet_spaces, visual_schedules
✓ Default to FE/training, exclude schools

Results ranked by:
- Section 41 approved providers (strong boost)
- Specialist SEND providers (boost)
- Distance
```

**Example 3: Specific Requirements**
```
Prompt: "Only show residential colleges for IT and computing courses, my child has dyslexia"

Extracted Intent:
✓ Residential: must (only residential)
✓ Vocational: it_computing
✓ SEND needs: dyslexia
✓ Non-residential providers filtered out

Results:
- Only residential providers shown
- Ranked by IT/computing relevance
- S41/specialist providers prioritized
```

### Graceful Degradation

If `OPENAI_API_KEY` is not configured:
- Falls back to deterministic keyword-based extraction
- All features still work, but with slightly lower accuracy
- Confidence score indicates extraction method used

### Response Structure

The `/instant` response includes:

```json
{
  "meta": {
    "used_postcode": "LS1 1AA",
    "used_radius_miles": 50,
    "extracted_intent": {
      "target_settings": ["fe_college", "training_provider"],
      "residential": "prefer",
      "vocational_areas": ["hospitality_catering"],
      "send_needs": [],
      "confidence": 0.7,
      "notes": "Extracted using keyword rules (LLM not available)"
    }
  },
  "instant_dossiers": [
    {
      "provider": { "name": "...", "residential": true },
      "score": 0.85,
      "score_breakdown": {
        "distance_component": 0.75,
        "residential_boost": 0.15,
        "vocational_component": 0.20,
        "send_component": 0.10
      },
      "match_reasons": [
        "Located 12.5 miles from your location",
        "✓ Residential provision available (preferred)",
        "✓ May offer courses in: Hospitality & Catering",
        "Provider likely offers SEND support",
        "Type: FE College"
      ],
      "quick_summary": "Provider Name | Vocational: Hospitality & Catering"
    }
  ]
}
```

## Testing

Run the comprehensive test suite:

```bash
python test_intent_matching.py
```

Tests cover:
- Intent extraction (residential, vocational, SEND needs)
- Provider type detection and filtering
- Scoring algorithm and match reason generation
- Edge cases and defaults
