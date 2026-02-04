import requests, time, json
from datetime import datetime, timezone

POSTCODES_IO = "https://api.postcodes.io/postcodes"

def norm_pc(pc: str) -> str:
    return (pc or "").upper().replace(" ", "")

def lookup_postcode(conn, postcode: str, sleep=0.2):
    if not postcode:
        return None
    key = norm_pc(postcode)
    cur = conn.cursor()
    cur.execute("SELECT lat, lon, terminated, meta_json FROM geocodes WHERE postcode_key=?", (key,))
    row = cur.fetchone()
    if row:
        lat, lon, term, meta = row
        return {"lat": lat, "lon": lon, "terminated": bool(term), "meta": json.loads(meta) if meta else None}

    # call postcodes.io
    time.sleep(sleep)  # be a respectful client
    r = requests.get(f"{POSTCODES_IO}/{key}", timeout=15)
    data = r.json()
    terminated = False
    lat = lon = None
    meta = None
    if data.get("status") == 200 and data.get("result"):
        res = data["result"]
        lat, lon = res["latitude"], res["longitude"]
        meta = res
        # 'terminated' is available on terminated endpoint; here if result is present it is live
    else:
        # Try the terminated endpoint to flag it clearly
        tr = requests.get(f"{POSTCODES_IO}/terminated/{key}", timeout=10)
        tdata = tr.json()
        if tdata.get("status") == 200 and tdata.get("result"):
            terminated = True
            meta = tdata["result"]

    cur.execute(
        "INSERT OR REPLACE INTO geocodes (postcode_key, postcode, lat, lon, terminated, meta_json, last_updated_utc) VALUES (?,?,?,?,?,?,?)",
        (key, postcode, lat, lon, int(terminated), json.dumps(meta), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    if lat is None or lon is None:
        return None
    return {"lat": lat, "lon": lon, "terminated": terminated, "meta": meta}