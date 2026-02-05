
# SEN College Finder – FastAPI Backend (Skeleton)

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
- `OPENAI_API_KEY`: OpenAI API key for GenAI prompt-based search features (required for prompt parameter)
- `OPENAI_MODEL`: OpenAI model to use (e.g., "gpt-4o-mini" or "gpt-4")

## Run the API
```powershell
powershell -ExecutionPolicy Bypass -File run_api.ps1
```
Open http://localhost:8000/docs

### Endpoints
- GET /health
- GET /instant?postcode=LS1%201AA&target_count=10
  - Optional: `prompt=<natural language description>` for GenAI-enhanced search
  - Example: `prompt=My child has ADHD and autism, needs quiet spaces and visual schedules, interested in hospitality and catering`
- POST /deep-dive  { "provider_id": "leeds_city_college_printworks" }

### GenAI Prompt-Based Search

The `/instant` endpoint now supports an optional `prompt` parameter for natural language search. When provided:

1. **Profile Extraction**: Uses CrewAI with OpenAI to extract structured information about:
   - Child's diagnoses (ADHD, Autism, Dyslexia, etc.)
   - Support needs (reading help, quiet environments, visual schedules, etc.)
   - Career aspirations (hospitality, catering, IT, etc.)

2. **Enhanced Scoring**: Extracted keywords improve provider matching and scoring

3. **Personalized Results**: 
   - `quick_summary` field includes relevant profile information
   - `why_it_matches` explains why each provider suits the child's needs
   - Extracted profile included in response `meta` for transparency

If the prompt feature is not needed or OPENAI_API_KEY is not set, the endpoint falls back to standard behavior.
