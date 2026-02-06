# Using the Intent Extraction Feature

## Quick Start Guide

### Basic Usage

The `/instant` endpoint now accepts a `prompt` parameter for natural language searches:

```bash
# Example 1: Residential catering search
curl "http://localhost:8000/instant?prompt=I+want+to+do+catering+at+a+residential+college&target_count=10"

# Example 2: SEND needs with specific vocational area
curl "http://localhost:8000/instant?prompt=My+child+has+autism+and+needs+quiet+spaces,+interested+in+computing&postcode=MK18+3BN"

# Example 3: Training provider search
curl "http://localhost:8000/instant?prompt=Looking+for+apprenticeships+in+construction&postcode=LS1+1AA"
```

### Response Format

The response now includes extracted intent in the metadata:

```json
{
  "meta": {
    "used_postcode": "MK18 3BN",
    "used_radius_miles": 30,
    "extracted_intent": {
      "target_settings": ["FE_COLLEGE", "TRAINING_PROVIDER"],
      "residential": "must",
      "vocational_areas": ["hospitality"],
      "send_needs": [],
      "confidence": "medium",
      "extraction_method": "fallback"
    }
  },
  "instant_dossiers": [
    {
      "provider": {
        "provider_id": "...",
        "name": "Example College",
        "residential": true,
        "s41": false
      },
      "score": 0.85,
      "distance_miles": 12.3,
      "why_it_matches": [
        "Located 12.3 miles from your location",
        "✓ Residential accommodation available (required)",
        "Likely offers: Hospitality",
        "Further Education college offering broad curriculum"
      ]
    }
  ]
}
```

### Natural Language Patterns

The system understands various natural language patterns:

#### Residential Preferences

**Must have residential**:
- "I want residential"
- "Need boarding school"
- "Live-in accommodation required"
- "Looking for a residential college"

**Prefer residential**:
- "Would prefer residential"
- "Ideally residential"
- "Residential would be good"

**No residential**:
- "Day provision only"
- "No residential"
- "Not residential"
- "Local day college"

#### Vocational Areas

**Hospitality/Catering**:
- "catering", "chef", "cookery", "hospitality"
- "I want to learn cooking"
- "Interested in the food industry"

**Computing/IT**:
- "computing", "IT", "digital", "programming"
- "Want to do web development"
- "Interested in technology"

**Construction**:
- "construction", "building", "plumbing", "electrical"
- "Want to be a carpenter"
- "Interested in trades"

**Other areas**: hair_beauty, land_based, retail, childcare, motor_vehicle

#### SEND Needs

**Autism/ASD**:
- "has autism", "autistic", "ASD", "Asperger's"

**ADHD**:
- "has ADHD", "attention deficit"

**Sensory**:
- "needs quiet spaces", "sensory needs", "visual schedules"

**Other needs**: literacy, numeracy, time_management, communication, physical, mental_health

### Example Use Cases

#### Use Case 1: Parent searching for residential SEND provision

**Prompt**: "My daughter has autism and ADHD, needs quiet spaces and visual schedules, interested in hospitality, looking for residential college"

**What happens**:
1. Intent extracted:
   - residential: "must" or "prefer"
   - vocational_areas: ["hospitality"]
   - send_needs: ["autism", "adhd", "sensory"]
   - target_settings: ["FE_COLLEGE", "TRAINING_PROVIDER"]

2. Filtering:
   - Excludes schools by default
   - Filters to residential providers (if "must")
   - Includes FE colleges and training providers

3. Ranking boosts:
   - +0.3 for residential (if must)
   - +0.2 for S41 approved
   - +0.15 for specialist SEND provision
   - +0.1 for hospitality keywords

4. Results show:
   - Residential SEND-focused colleges
   - With hospitality courses
   - Clear match_reasons explaining why

#### Use Case 2: Youth worker searching for local FE options

**Prompt**: "16 year old interested in construction, has dyslexia, day provision only"

**What happens**:
1. Intent extracted:
   - residential: "exclude"
   - vocational_areas: ["construction"]
   - send_needs: ["literacy"]
   - target_settings: ["FE_COLLEGE", "TRAINING_PROVIDER"]

2. Filtering:
   - Excludes residential providers
   - Includes local FE colleges and training providers
   - Excludes schools

3. Results show:
   - Non-residential local colleges
   - With construction courses
   - SEND support available

### Configuration

#### With OpenAI API Key (LLM-based extraction)

```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Benefits:
- More nuanced intent understanding
- Better handling of complex prompts
- Higher confidence scores
- Can understand context and implications

#### Without OpenAI API Key (Fallback mode)

```bash
# .env file
OPENAI_API_KEY=
```

Benefits:
- Zero external dependencies
- Deterministic results
- No API costs
- Still handles common patterns well
- Suitable for development and testing

### Frontend Integration

```javascript
// Example React/TypeScript integration

async function searchProviders(userPrompt: string, postcode: string) {
  const params = new URLSearchParams({
    prompt: userPrompt,
    postcode: postcode,
    target_count: '10'
  });
  
  const response = await fetch(`/instant?${params}`);
  const data = await response.json();
  
  // Access extracted intent
  console.log('Detected intent:', data.meta.extracted_intent);
  
  // Display results with match reasons
  data.instant_dossiers.forEach(result => {
    console.log(result.provider.name);
    console.log('Match reasons:', result.why_it_matches);
  });
}

// Example usage
searchProviders(
  "I want to do catering at a residential college",
  "MK18 3BN"
);
```

### Best Practices

1. **Be specific in prompts**: More detail = better matching
   - Good: "My child has autism, needs quiet spaces, interested in computing"
   - Less good: "Need a college"

2. **Mention key requirements**: Residential, vocational area, SEND needs
   - These drive the matching algorithm

3. **Use natural language**: No need for structured formats
   - "I want to..." works fine
   - So does "Looking for..." or "Need..."

4. **Review match_reasons**: They explain why each provider matched
   - Helps users understand the results
   - Builds trust in the system

5. **Fallback gracefully**: System works without API key
   - Development environments don't need OpenAI
   - Production can choose based on needs

### Troubleshooting

**Q: Why aren't schools showing up?**
A: By default, schools are excluded. Mention "school" or "sixth form" in your prompt to include them.

**Q: Why is intent confidence "low"?**
A: Prompt may be vague or missing key details. Add more specific information about needs and interests.

**Q: Why are match_reasons generic?**
A: May be using fallback mode, or providers lack detailed data. More specific prompts help.

**Q: How do I include schools?**
A: Mention them explicitly: "Looking for school or college with IT"

**Q: What if no residential providers found?**
A: Try expanding radius, or change "residential: must" to "residential: prefer" by rephrasing prompt.

### API Parameters (Backward Compatible)

The `/instant` endpoint still accepts all previous parameters:

```bash
# Mix prompt with traditional parameters
curl "http://localhost:8000/instant?\
prompt=autism+and+hospitality&\
postcode=MK18+3BN&\
radius_miles=50&\
residential_mode=include&\
target_count=10"
```

All parameters work together:
- `prompt` - New: Natural language search
- `postcode` - Location for search
- `radius_miles` - Search radius
- `residential_mode` - Include/exclude/only residential
- `target_count` - Number of results
- Traditional scoring weights (w_send, w_asp, w_dist)

### Testing

Run the test suite to verify functionality:

```bash
# Unit tests
python test_intent_matching.py

# Integration tests (requires database)
python test_instant_integration.py

# Existing tests (backward compatibility)
python test_genai_features.py
```

All tests should pass ✓

---

For more details, see:
- `INTENT_MATCHING_IMPLEMENTATION.md` - Technical implementation details
- `INTENT_MATCHING_SECURITY.md` - Security analysis
- `README.md` - General project information
