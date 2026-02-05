# Frontend Integration Guide

## Overview
This document describes the changes needed in the frontend repository (mikepotts/sen-college-frontend) to integrate with the new GenAI prompt-based search feature.

## Backend Changes Completed
The backend now supports:
- Optional `prompt` query parameter on GET `/instant` endpoint
- Enhanced dossier fields: `quick_summary` and `why_it_matches` with profile-based personalization
- Extracted profile returned in response `meta.extracted_profile` for transparency

## Frontend Changes Required

### 1. Add Prompt Input to Search Form (`src/App.jsx`)

Add a textarea input to allow users to describe their child's needs in natural language:

```jsx
// Add state for prompt
const [prompt, setPrompt] = useState('');

// In the search form, add:
<div className="form-group">
  <label htmlFor="prompt">
    Tell us about your child (optional)
    <small>Describe their needs, diagnoses, and interests in your own words</small>
  </label>
  <textarea
    id="prompt"
    className="form-control"
    rows="3"
    value={prompt}
    onChange={(e) => setPrompt(e.target.value)}
    placeholder="e.g., My child has ADHD and autism, needs quiet spaces and visual schedules, interested in hospitality and catering"
  />
</div>
```

### 2. Pass Prompt to Backend API

Update the API call to include the prompt parameter:

```jsx
// In the search/fetch function:
const params = new URLSearchParams({
  postcode: postcode,
  radius_miles: radiusMiles,
  target_count: targetCount,
  residential_mode: residentialMode,
  national_for_residential: nationalForResidential,
  // Add prompt if provided
  ...(prompt && { prompt: prompt })
});

const response = await fetch(`${API_BASE_URL}/instant?${params}`);
```

### 3. Display Enhanced Fields (Already Supported)

The UI should already render `quick_summary` and `why_it_matches` fields from dossiers. Verify they display correctly:

```jsx
// These fields are already in the dossier response:
{
  "quick_summary": "Provider Name - Interests: hospitality, catering | Support for: ADHD, Autism",
  "why_it_matches": [
    "Located 12.5 miles from your postcode",
    "May offer courses related to: hospitality, catering",
    "Provider has SEND support capabilities",
    "Section 41 approved for SEND provision"
  ]
}
```

### 4. (Optional) Display Extracted Profile

If you want to show users what was extracted from their prompt:

```jsx
// Access from response.meta.extracted_profile
{data.meta?.extracted_profile && (
  <div className="extracted-profile">
    <h4>We understood:</h4>
    <ul>
      {data.meta.extracted_profile.diagnoses?.length > 0 && (
        <li>Diagnoses: {data.meta.extracted_profile.diagnoses.join(', ')}</li>
      )}
      {data.meta.extracted_profile.needs?.length > 0 && (
        <li>Needs: {data.meta.extracted_profile.needs.join(', ')}</li>
      )}
      {data.meta.extracted_profile.aspirations?.length > 0 && (
        <li>Interests: {data.meta.extracted_profile.aspirations.join(', ')}</li>
      )}
    </ul>
    <p className="text-muted">{data.meta.extracted_profile.summary}</p>
  </div>
)}
```

### 5. Error Handling

The prompt feature fails gracefully on the backend, but you may want to show a message if extraction fails:

```jsx
// If prompt was provided but no profile was extracted (unlikely but possible)
{prompt && !data.meta?.extracted_profile && (
  <div className="alert alert-info">
    Searching with your description... (AI analysis not available)
  </div>
)}
```

## Testing Steps

1. **Without prompt**: Ensure existing search still works
2. **With prompt**: Add a natural language description and verify:
   - Request includes `prompt` parameter
   - Results show personalized `quick_summary`
   - `why_it_matches` includes profile-specific reasons
3. **Without API key**: Verify graceful degradation (search works without GenAI enhancement)

## Example User Flow

1. User enters postcode: "LS1 1AA"
2. User enters description: "My child has dyslexia and ADHD, loves cooking and wants to be a chef, needs support with reading and organization"
3. User clicks search
4. Backend extracts:
   - Diagnoses: [Dyslexia, ADHD]
   - Needs: [reading support, organization]
   - Aspirations: [cooking, chef]
5. Results show:
   - Providers ranked with enhanced scoring
   - Quick summaries mention cooking/chef interests
   - Why it matches explains ADHD/dyslexia support

## Backward Compatibility

All changes are backward compatible:
- Prompt parameter is optional
- Existing searches without prompt work exactly as before
- No changes to existing dossier structure (only enhanced content)

## Notes

- Keep the prompt textarea optional with clear labeling
- Consider adding example prompts as placeholder text
- The feature works best with conversational, detailed descriptions
- Empty or very short prompts are handled gracefully
