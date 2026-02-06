import logging
logging.basicConfig(level=logging.DEBUG)
import os
from pathlib import Path
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH =PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)
print("degub USSER POSTCODE ",os.getenv("USER_POSTCODE"))
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
#from typing import Optional, Literal
from config import RunConfig, ScoringConfig
from tools.local_provider_builder import build_local_non_residential, load_catalog
from tools.deep_dive import run_deep_dive
from fastapi.responses import JSONResponse
from fastapi.requests import Request


from typing import Optional, Literal, List, Dict, Any
from fastapi import Query, HTTPException
from tools.geo import geocode_postcode, haversine_miles
from tools.scoring import blended_score, HOSPITALITY_KEYWORDS, SEND_KEYWORDS, keyword_hits
from tools.provider_repository import fetch_nearby_providers  # DB-backed
from datetime import datetime, timezone

# Constants
MAX_PROMPT_LOG_LENGTH = 100
DEFAULT_WHY_IT_MATCHES = [
    "Distance and basic suitability weighting applied.",
    "Full SEND/course detail appears in Deep Dive."
]



app = FastAPI(title="SEN College Finder API", version="0.1.0")
origins=["http://localhost:5173","http://127.0.0.1:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    print("FAST API GOT REQUEST", request.method, request.url)
    print("REQ: ", request.method, request.url)
    resp = await call_next(request)
    return resp

@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    # Log request details to correlate with frontend calls
    print("🔥 UNCAUGHT ERROR @", request.url)
    print("🔥 EXC:", repr(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal error: {repr(exc)}"},
    )

@app.get("/health")
def health():
    return {"status":"ok"}

class DeepDiveIn(BaseModel):
    provider_id: str

@app.get("/debug/providers-source")
def debug_providers_source():
    # Try JSON catalog
    from tools.local_provider_builder import load_catalog
    try:
        cat = load_catalog()
        return {
            "source": "JSON catalog (legacy)",
            "count": len(cat),
            "sample": cat[:3]
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/instant")
def instant(
    
    postcode: Optional[str] = Query(None, description="UK postcode; falls back to .env if missing"),
    # Simple single-radius mode (recommended)
    radius_miles: Optional[int] = Query(None, ge=1, le=500, description="If set, search uses this fixed radius"),
    # Legacy expanding radius mode (kept for backward-compat)
    start_radius_miles: int = Query(30, ge=1, le=500),
    expand_step_miles: int   = Query(10, ge=0, le=200),
    max_radius_miles: int    = Query(80, ge=1, le=500),

    residential_mode: Literal["exclude", "include", "only"] = Query("include"),
    national_for_residential: bool = Query(True),
    target_count: int = Query(10, ge=1, le=100),

    # scoring weights
    w_send: float = Query(0.40, ge=0.0, le=1.0),
    w_asp: float  = Query(0.35, ge=0.0, le=1.0),
    w_dist: float = Query(0.25, ge=0.0, le=1.0),
    
    # NEW: GenAI prompt-based search
    prompt: Optional[str] = Query(None, description="Natural language description of child needs, diagnoses, and aspirations"),
):
    print("DEBUG /instant params:", {
    "postcode": postcode,
    "radius_miles": radius_miles,
    "start_radius_miles": start_radius_miles,
    "expand_step_miles": expand_step_miles,
    "max_radius_miles": max_radius_miles,
    "residential_mode": residential_mode,
    "national_for_residential": national_for_residential,
    "target_count": target_count,
    "prompt": prompt[:MAX_PROMPT_LOG_LENGTH] if prompt else None
    })
    """
    DB-backed /instant:

    - Uses providers from SQLite (NOT the legacy JSON).
    - radius_miles: if provided => fixed-radius search.
    - else expands: start_radius_miles -> ... -> max_radius_miles until target_count or max reached.
    - residential_mode: 'exclude' | 'include' | 'only'
    - national_for_residential: when True and residential_mode != 'exclude', returns residential providers nationally
      (i.e., not restricted by the local radius), ranked primarily by distance (if available) + placeholder scores.
    - prompt: optional natural language description for GenAI-enhanced search with intent extraction
    """
    # ----- 0) Extract intent from prompt if provided
    extracted_intent = None
    if prompt:
        from tools.intent_extractor import extract_intent_from_prompt
        extracted_intent = extract_intent_from_prompt(prompt)
        if extracted_intent:
            print("DEBUG: Extracted intent:", extracted_intent.model_dump())
    
    # ----- 1) set up config / scoring
    cfg = RunConfig()
    cfg.scoring = ScoringConfig(w_distance=w_dist, w_aspiration=w_asp, w_send_fit=w_send)

    user_pc = (postcode or os.getenv("USER_POSTCODE", cfg.location.user_postcode) or "").strip()
    if not user_pc:
        raise HTTPException(status_code=400, detail="A valid postcode is required.")

    # ----- 1) geocode the user postcode (fail fast with helpful message)
    user_geo = geocode_postcode(user_pc)
    if not user_geo:
        raise HTTPException(
            status_code=400,
            detail=f"Postcode '{user_pc}' not found/terminated or unsupported. Try a nearby valid postcode."
        )
    user_lat, user_lon, _meta = user_geo

    # ----- 2) get DB candidates (with lat/lon) — non-residential set for local ranking
    include_res_for_local = False if residential_mode == "only" else True  # we will filter non-res later
    # Pull generously (repository returns rows with lat/lon; we filter/score below)
    # We ask for a big max_distance to get a pool; we will do our own radius filtering locally.
    local_pool = fetch_nearby_providers(user_lat, user_lon, include_residential=include_res_for_local, max_distance_miles=9999)

    # Ensure records have lat/lon
    local_pool = [r for r in local_pool if isinstance(r.get("lat"), (int,float)) and isinstance(r.get("lon"), (int,float))]

    # ----- 3) compute distances & select local candidates under radius
    def with_distance(row: Dict[str, Any]) -> Dict[str, Any]:
        d = haversine_miles(user_lat, user_lon, float(row["lat"]), float(row["lon"]))
        r2 = dict(row)
        r2["distance_miles"] = round(d, 1)
        return r2

    local_pool = [with_distance(r) for r in local_pool]

    # ----- 3.5) Filter by provider type based on intent
    if extracted_intent:
        from tools.provider_type_detector import matches_target_settings
        # Filter providers by target settings (excludes schools by default)
        local_pool = [r for r in local_pool if matches_target_settings(r, extracted_intent.target_settings)]
    else:
        # Default behavior: exclude schools unless explicitly targeting them
        from tools.provider_type_detector import infer_provider_type
        local_pool = [r for r in local_pool if infer_provider_type(r) != "SCHOOL"]

    # Filter to non-residential for local_non_residential bucket (the UI's "instant_dossiers")
    # But respect intent-based residential preference
    if extracted_intent and extracted_intent.residential.value == "must":
        # If residential is MUST, only show residential providers
        non_res = [r for r in local_pool if r.get("is_residential")]
    else:
        # Standard behavior: show non-residential for local results
        non_res = [r for r in local_pool if not r.get("is_residential")]
    # If fixed-radius provided, use it; else expand until we reach target_count or max
    if radius_miles is not None:
        used_radius = radius_miles
        local_within = [r for r in non_res if r["distance_miles"] <= used_radius]
    else:
        used_radius = start_radius_miles
        while True:
            local_within = [r for r in non_res if r["distance_miles"] <= used_radius]
            if len(local_within) >= target_count or used_radius >= max_radius_miles or expand_step_miles == 0:
                break
            used_radius += expand_step_miles

    # ----- 4) scoring with intent-based enhancements
    def score_row(r: Dict[str, Any]) -> Dict[str, Any]:
        from tools.scoring import intent_based_score
        
        # Use intent-based scoring
        score, breakdown, match_reasons = intent_based_score(
            provider=r,
            distance_miles=r["distance_miles"],
            radius_miles=max(used_radius, 0.01),
            intent=extracted_intent,
            cfg=cfg.scoring
        )
        
        r2 = dict(r)
        r2["score"] = round(score, 4)
        r2["score_breakdown"] = breakdown
        r2["score_breakdown"]["weights"] = {
            "distance": cfg.scoring.w_distance,
            "aspiration": cfg.scoring.w_aspiration,
            "sendfit": cfg.scoring.w_send_fit
        }
        r2["match_reasons"] = match_reasons
        return r2

    local_scored = [score_row(r) for r in local_within]
    local_scored.sort(key=lambda x: (-x["score"], x["distance_miles"]))
    local_scored = local_scored[:target_count]

    # ----- 5) residential results (national or local depending on flag/mode)
    residential_dossiers: List[Dict[str, Any]] = []
    if residential_mode in ("include", "only"):
        # If national_for_residential=True → fetch residential across the DB (not restricted by radius)
        if national_for_residential:
            # Pull a big pool (include_residential=True), then filter to residential in code
            res_pool = fetch_nearby_providers(user_lat, user_lon, include_residential=True, max_distance_miles=9999)
            res_pool = [r for r in res_pool if r.get("is_residential") and isinstance(r.get("lat"), (int,float)) and isinstance(r.get("lon"), (int,float))]
            res_pool = [with_distance(r) for r in res_pool]
            # You can score similarly (distance light-weight in nat. context)
            residential_scored = [score_row(r) for r in res_pool]
            residential_scored.sort(key=lambda x: (x["distance_miles"], x["provider_id"]))
            residential_dossiers = residential_scored[:max(target_count, 50)]  # show a reasonable slice
        else:
            # local-only residential (same used_radius)
            res_local = [r for r in local_pool if r.get("is_residential") and r["distance_miles"] <= used_radius]
            residential_scored = [score_row(r) for r in res_local]
            residential_scored.sort(key=lambda x: (-x["score"], x["distance_miles"]))
            residential_dossiers = residential_scored[:target_count]

        # If 'only', blank the non-residential local list
        if residential_mode == "only":
            local_scored = []

    # ----- 6) convert to dossier format expected by the UI
    def to_dossier(row: Dict[str, Any]) -> Dict[str, Any]:
        key_links = []
        if row.get("website"):
            key_links.append({"label": "Website", "url": row["website"]})
        who = [
            {
                "role": "SEND / Inclusive Learning",
                "suggestion": "Ask about EHCP support, reasonable adjustments, transition visits and quieter sessions."
            },
            {
                "role": "Admissions / Course Team",
                "suggestion": "Ask about course levels, facilities and work placements."
            }
        ]
        badges = ["SEND-first"]
        if not row.get("is_residential"):
            badges.insert(0, "Local")
        else:
            badges.insert(0, "Residential")
        
        # Use match_reasons from scoring if available, otherwise generate legacy ones
        quick_summary = ""
        why_it_matches = row.get("match_reasons", list(DEFAULT_WHY_IT_MATCHES))
        
        # Generate intent-based quick_summary if intent exists
        if extracted_intent:
            summary_parts = [row['name']]
            
            if extracted_intent.vocational_areas:
                voc_areas = [v.replace("_", " ").title() for v in extracted_intent.vocational_areas[:2]]
                summary_parts.append(f"Vocational: {', '.join(voc_areas)}")
            
            if extracted_intent.send_needs:
                needs = [n.replace("_", " ").title() for n in extracted_intent.send_needs[:2]]
                summary_parts.append(f"SEND Support: {', '.join(needs)}")
            
            quick_summary = " | ".join(summary_parts)

        return {
            "provider": {
                "provider_id": row["provider_id"],
                "name": row["name"],
                "postcode": row.get("postcode"),
                "residential": bool(row.get("is_residential")),
                "s41": bool(row.get("s41_approved")),
                "links": {"Website": row.get("website")} if row.get("website") else {}
            },
            "badges": badges,
            "distance_miles": row.get("distance_miles"),
            "score": row.get("score"),
            "score_breakdown": row.get("score_breakdown"),
            "quick_summary": quick_summary,
            "why_it_matches": why_it_matches,
            "key_links": key_links,
            "who_to_contact": who,
            "open_days_hint": {
                "best_next_step": "Check the website or contact SEND for open event details.",
                "link": row.get("website")
            },
        }

    instant_dossiers = [to_dossier(r) for r in local_scored]
    residential_results = [to_dossier(r) for r in residential_dossiers]

    result = {
        "meta": {
            "used_postcode": user_pc,
            "used_radius_miles": used_radius if radius_miles is None else radius_miles,
            "weights": {"send": w_send, "aspiration": w_asp, "distance": w_dist},
            "residential_mode": residential_mode,
            "national_for_residential": national_for_residential,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "extracted_intent": extracted_intent.model_dump() if extracted_intent else None  # Include for transparency
        },
        "local_non_residential": {
            "user_postcode": user_pc,
            "used_radius_miles": used_radius if radius_miles is None else radius_miles,
            "providers": [  # raw subset for debug/analytics; safe to keep minimal
                {
                    "provider_id": r["provider_id"],
                    "name": r["name"],
                    "distance_miles": r.get("distance_miles"),
                    "is_residential": bool(r.get("is_residential")),
                } for r in local_scored
            ],
        },
        "instant_dossiers": instant_dossiers,        # non-residential local list used by the UI
        "residential_results": residential_results,  # optional residential bucket (national or local)
    }

    if not instant_dossiers and not residential_results:
        result["message"] = (
            "No providers found with the current settings. "
            "Try increasing the radius or enabling national residential results."
        )

    return result

@app.post("/deep-dive")
def deep_dive(payload: DeepDiveIn = Body(...)):
    """
    Perform a deep dive on a specific provider using SQLite database.
    
    Fetches provider details from the database and runs deep dive analysis
    using the provider's website as the primary source.
    """
    from tools.provider_repository import fetch_by_id
    
    provider = fetch_by_id(payload.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider not found: {payload.provider_id}")
    
    # Use provider website as primary link for deep dive
    links = {}
    if provider.get("website"):
        links["Website"] = provider["website"]
    
    return run_deep_dive(payload.provider_id, links)
