
from tools.geo import geocode_postcode, haversine_miles
from tools.scoring import keyword_hits, blended_score, HOSPITALITY_KEYWORDS, SEND_KEYWORDS
import json
from pathlib import Path

def load_catalog():
    p = Path(__file__).resolve().parent.parent / "data" / "provider_catalog.json"
    return json.loads(p.read_text(encoding="utf-8"))

def geocode_provider_if_needed(provider):
    if provider.get("lat") is not None and provider.get("lon") is not None:
        return provider
    pc = provider.get("postcode")
    if not pc: return None
    geo = geocode_postcode(pc)
    if not geo: return None
    lat, lon, _ = geo
    p2 = dict(provider)
    p2["lat"], p2["lon"] = lat, lon
    return p2

def build_local_non_residential(cfg):
    user_geo = geocode_postcode(cfg.location.user_postcode)
    if not user_geo:
        return {"error":"Could not geocode user postcode","providers":[]}
    u_lat, u_lon, _ = user_geo

    catalog = load_catalog()
    candidates = [p for p in catalog if not p.get("residential", False)]
    enriched=[]
    for p in candidates:
        p2 = geocode_provider_if_needed(p)
        if not p2: continue
        d = haversine_miles(u_lat, u_lon, p2["lat"], p2["lon"])
        p2["distance_miles"] = round(d,1)
        enriched.append(p2)

    radius = cfg.location.local_radius_miles
    while True:
        within = [p for p in enriched if p["distance_miles"] <= radius]
        if len(within) >= cfg.location.local_target_count or radius >= cfg.location.local_max_radius_miles:
            break
        radius += cfg.location.local_expand_step_miles

    scored=[]
    for p in within:
        text = " ".join([str(p.get("notes","")), " ".join(p.get("tags",[]))])
        a_hits = keyword_hits(text, HOSPITALITY_KEYWORDS)
        s_hits = keyword_hits(text, SEND_KEYWORDS)
        score, dcomp, acomp, scomp = blended_score(p["distance_miles"], radius, a_hits, s_hits, cfg.scoring)
        p2 = dict(p)
        p2["score"] = round(score,4)
        p2["score_breakdown"] = {
            "distance_component": round(dcomp,4),
            "aspiration_component": round(acomp,4),
            "sendfit_component": round(scomp,4),
            "weights": {"distance": cfg.scoring.w_distance, "aspiration": cfg.scoring.w_aspiration, "sendfit": cfg.scoring.w_send_fit}
        }
        scored.append(p2)

    scored.sort(key=lambda x: (-x["score"], x["distance_miles"]))

    return {
        "user_postcode": cfg.location.user_postcode,
        "used_radius_miles": radius,
        "count": min(cfg.location.local_target_count, len(scored)),
        "providers": scored[:cfg.location.local_target_count]
    }
