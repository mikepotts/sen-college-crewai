import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "providers.sqlite"

def get_conn():
    return sqlite3.connect(str(DB_PATH))

def fetch_nearby_providers(lat: float, lon: float, include_residential: bool, max_distance_miles: float) -> List[Dict[str,Any]]:
    """
    Returns a coarse candidate set; we filter/score later.
    For SQLite we don't have geospatial index, so we pre-filter by a bounding box heuristic,
    then compute haversine in Python (like you already do).
    """
    conn = get_conn()
    c = conn.cursor()
    # Pull a reasonable tranche (e.g. 5k rows) to compute precise distances in code
    # You can refine: fetch all ENG or by rough lat/lon window.
    sql = "SELECT provider_id, name, postcode, lat, lon, is_residential, s41_approved, website FROM providers WHERE lat IS NOT NULL AND lon IS NOT NULL"
    if not include_residential:
        sql += " AND (is_residential=0 OR is_residential IS NULL)"
    rows = c.execute(sql).fetchall()
    conn.close()

    cols = ["provider_id","name","postcode","lat","lon","is_residential","s41_approved","website"]
    out = [dict(zip(cols,r)) for r in rows]
    return out

def fetch_by_ids(ids: List[str]) -> Dict[str,Dict[str,Any]]:
    if not ids: return {}
    conn = get_conn()
    c = conn.cursor()
    qmarks = ",".join(["?"]*len(ids))
    rows = c.execute(f"SELECT provider_id,name,postcode,lat,lon,is_residential,s41_approved,website FROM providers WHERE provider_id IN ({qmarks})", ids).fetchall()
    conn.close()
    cols = ["provider_id","name","postcode","lat","lon","is_residential","s41_approved","website"]
    return {r[0]: dict(zip(cols,r)) for r in rows}