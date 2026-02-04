import os, io, json, hashlib
from datetime import datetime, timezone
import pandas as pd
import requests
from pathlib import Path

from etl_config import DB_PATH
from db import get_conn, upsert_provider
from geocode import lookup_postcode

def pid_from(ukprn: str, name: str, postcode: str):
    if ukprn and str(ukprn).strip():
        return str(ukprn).strip()
    h = hashlib.sha256(f"{(name or '').strip()}|{(postcode or '').strip()}".encode("utf-8")).hexdigest()
    return f"gen_{h[:20]}"

def run(xlsx_url: str):
    conn = get_conn(DB_PATH)
    now = datetime.now(timezone.utc).isoformat()

    r = requests.get(xlsx_url, timeout=60)
    r.raise_for_status()
    # Section 41 workbook – first sheet generally holds the data
    df = pd.read_excel(io.BytesIO(r.content), engine="openpyxl")

    # Columns vary slightly over time; try friendly getters
    def g(row, *names):
        for n in names:
            if n in row and pd.notna(row[n]):
                return str(row[n]).strip()
        return ""

    for _, row in df.iterrows():
        name     = g(row, "Name", "Institution name", "Provider name")
        ukprn    = g(row, "UKPRN", "Ukprn")
        website  = g(row, "Website", "Website address", "URL")
        postcode = g(row, "Postcode", "Post code")

        if not name:
            continue

        pid = pid_from(ukprn, name, postcode)

        geo = None
        if postcode:
            geo = lookup_postcode(conn, postcode)

        # Simple residential heuristic (many s41 SPIs offer residential boarding)
        notes = " ".join([g(row, "Type of institution","Type"), g(row, "Notes"), g(row, "Specialism")]).lower()
        is_res = 1 if any(w in notes for w in ["residential", "boarding"]) else 0

        rec = {
            "provider_id": pid,
            "ukprn": ukprn or None,
            "name": name,
            "website": website or None,
            "email": None,
            "phone": None,
            "address": None,
            "postcode": postcode or None,
            "lat": (geo or {}).get("lat"),
            "lon": (geo or {}).get("lon"),
            "country": "ENG",  # s41 list is England & Wales; you can refine if the sheet includes LA/country
            "provider_type": "special_post16" if "post-16" in notes or "post 16" in notes else None,
            "is_residential": is_res,
            "is_specialist": 1,
            "s41_approved": 1,
            "ofsted_urn": None,
            "ofsted_url": None,
            "source_flags": json.dumps({"s41": True}),
            "first_seen_utc": now,
            "last_seen_utc": now
        }
        upsert_provider(conn, rec)

    conn.commit()
    print("s41 import complete.")

if __name__ == "__main__":
    url = os.environ.get("S41_XLSX_URL")
    if not url:
        raise SystemExit("Set S41_XLSX_URL env var to the direct XLSX URL of the Section 41 list.")
    run(url)