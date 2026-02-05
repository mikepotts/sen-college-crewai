# GenAI Prompt-Based Search Implementation Summary

## Overview
This implementation adds GenAI-powered prompt-based search capabilities to the SEN College Finder backend using CrewAI and OpenAI, along with SQLite integration for the deep-dive feature.

## Changes Made

### 1. Dependencies (`requirements.txt`)
- **Added**: `crewai>=0.28.0` - CrewAI framework for AI agent orchestration
- **Added**: `openai>=1.0.0` - OpenAI API client for LLM access

### 2. Environment Configuration (`.env.example`)
Updated to include:
- `OPENAI_API_KEY`: Required for GenAI prompt extraction
- `OPENAI_MODEL`: Model selection (default: gpt-4o-mini)
- Clear documentation that these are required for the prompt feature

### 3. Profile Extraction (`tools/profile_extractor.py`)
**New module** that provides:
- `extract_profile_from_prompt()`: Extracts structured data from natural language prompts
  - Uses CrewAI Agent with specialized SEND education expertise
  - Extracts: diagnoses, needs, aspirations, keywords, and summary
  - Gracefully handles missing API key (returns None, allows fallback)
  
- `enhance_scoring_with_profile()`: Calculates enhanced keyword matches
  - Uses extracted profile to improve relevance scoring
  - Separates aspiration vs SEND keyword hits

**Architecture**:
- Uses CrewAI's LLM class (not langchain_openai) for simplicity
- Single sequential agent/task for efficient extraction
- Structured output parsing with clear format expectations

### 4. Provider Repository (`tools/provider_repository.py`)
**Added**:
- `fetch_by_id()`: Fetches single provider from SQLite by ID
  - Returns dictionary with all provider fields
  - Used by /deep-dive endpoint for SQLite migration

### 5. API Endpoints (`api/main.py`)

#### GET /instant Endpoint
**Added parameter**:
- `prompt: Optional[str]` - Natural language description of child needs

**Enhanced functionality**:
1. Profile extraction when prompt is provided
2. Enhanced scoring using extracted keywords
3. Personalized dossier fields:
   - `quick_summary`: Profile-aware summary
   - `why_it_matches`: Personalized match explanations
4. Extracted profile in response `meta` for transparency

**Graceful degradation**:
- If no API key: falls back to standard behavior
- If extraction fails: falls back to standard behavior
- Existing logic preserved (distance, radius, residential mode, etc.)

#### POST /deep-dive Endpoint
**Migration to SQLite**:
- Now uses `fetch_by_id()` from provider_repository
- No longer depends on legacy JSON catalog
- Uses provider.website as primary deep-dive link
- Returns 404 with proper error message for missing providers

### 6. Documentation (`README.md`)
**Added sections**:
- Environment Variables documentation
- GenAI Prompt-Based Search feature description
- Example prompt usage
- Explanation of how extracted profiles enhance results

### 7. Testing (`test_genai_features.py`)
**Comprehensive test suite** covering:
1. Profile extraction (graceful degradation without API key)
2. Provider repository SQLite integration
3. Enhanced scoring with mock profiles
4. API structure validation (endpoint parameters, OpenAPI spec)

### 8. Git Configuration (`.gitignore`)
Updated to exclude:
- `__pycache__/` directories
- Python bytecode files (`.pyc`, `.pyo`, `.pyd`)
- Build artifacts

## Key Design Decisions

### 1. Minimal Changes Principle
- Preserved all existing endpoint behavior and parameters
- Prompt feature is purely additive (optional parameter)
- No breaking changes to existing API contracts
- Fallback to standard behavior if GenAI is unavailable

### 2. Graceful Degradation
- System works without OPENAI_API_KEY configured
- If extraction fails, search continues with standard scoring
- Logging warnings but not failing requests

### 3. SQLite Migration
- Deep-dive now uses SQLite (single source of truth)
- Removed dependency on legacy JSON catalog
- Proper error handling for missing providers

### 4. Transparency
- Extracted profile included in response metadata
- Users can see what was extracted from their prompt
- Helps with debugging and trust

## Testing Results

All tests passing:
- ✓ Profile extraction graceful degradation
- ✓ SQLite provider repository integration
- ✓ Enhanced scoring with keyword matching
- ✓ API structure with prompt parameter
- ✓ Deep-dive endpoint using SQLite
- ✓ Health endpoint operational

## Usage Examples

### Basic Search (no prompt)
```bash
GET /instant?postcode=LS1%201AA&radius_miles=30&target_count=10
```
Behavior: Standard distance-based search with minimal scoring

### Enhanced Search (with prompt)
```bash
GET /instant?postcode=LS1%201AA&radius_miles=30&target_count=10&prompt=My%20child%20has%20ADHD%20and%20autism,%20needs%20quiet%20spaces,%20interested%20in%20hospitality
```
Behavior: 
1. Extracts profile (diagnoses: ADHD, autism; needs: quiet spaces; aspirations: hospitality)
2. Uses keywords to enhance scoring
3. Personalizes quick_summary and why_it_matches
4. Returns extracted profile in meta

### Deep Dive
```bash
POST /deep-dive
{"provider_id": "gen_f0af7f35f26bf26db680"}
```
Behavior: Fetches provider from SQLite, runs deep dive with website link

## Security Considerations

1. **API Key Protection**: 
   - API key only read from environment variables
   - Never exposed in responses or logs
   - Not required for basic functionality

2. **Input Validation**:
   - Prompt is optional and sanitized by FastAPI
   - Provider IDs validated against database

3. **Error Handling**:
   - Exceptions logged but not exposed to users
   - Graceful fallback prevents service disruption

## Future Enhancements (Not in This PR)

1. Cache extracted profiles to reduce API calls
2. Add provider descriptions/tags to database for better keyword matching
3. Support for other LLM providers (Azure OpenAI, Anthropic)
4. Enhanced prompt templates for specific use cases
5. Feedback loop to improve extraction accuracy

## Migration Notes

### For Deployment
1. Install new dependencies: `pip install -r requirements.txt`
2. Set `OPENAI_API_KEY` and `OPENAI_MODEL` in environment
3. Test with and without API key to verify graceful degradation

### Breaking Changes
**None** - All changes are backward compatible

### Database Requirements
- SQLite database must have providers table with required columns
- No schema changes needed
