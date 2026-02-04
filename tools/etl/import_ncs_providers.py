import os, io, csv, json, hashlib
from datetime import datetime, timezone
import pandas as pd
import requests
from pathlib import Path

from etl_config import DATA_DIR, DB_PATH, NCS_LIVE_PROVIDERS_CSV
from db import get_conn, ensure_schema, upsert_provider
from geocode import lookup_postcode

SCHEMA_SQL = (Path(__file__).resolve().parent / "schema.sql").read_text(encoding="utf-8")

def pid_from(ukprn: str, name: str, postcode: str):
    if ukprn and str(ukprn).strip():
        return str(ukprn).strip()
    h = hashlib.sha256(f"{(name or '').strip()}|{(postcode or '').strip()}".encode("utf-8")).hexdigest()
    return f"gen_{h[:20]}"

def run(ncs_csv_url: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_conn(DB_PATH)
    ensure_schema(conn, SCHEMA_SQL)

    # Download CSV
    r = requests.get(ncs_csv_url, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    print("DF", df)
    now = datetime.now(timezone.utc).isoformat()

    for _, row in df.iterrows():
        print("ROW",row)
        name = str(row.get("ProviderName") or row.get("PROVIDER_NAME") or "").strip()
        ukprn = str(row.get("UKPRN") or row.get("Ukprn") or "").strip()
        website = str(row.get("Website") or row.get("website") or "").strip()
        phone = str(row.get("Telephone") or row.get("Phone") or "").strip()
        email = str(row.get("Email") or "").strip()
        address = str(row.get("Address") or "").strip()
        postcode = str(row.get("CONTACT_POSTCODE") or row.get("Post Code") or "").strip().upper()

        if not name:
            print("CONTINUE",name)
            continue

        pid = pid_from(ukprn, name, postcode)

        geo = None
        if postcode:
            geo = lookup_postcode(conn, postcode)

        rec = {
            "provider_id": pid,
            "ukprn": ukprn or None,
            "name": name,
            "website": website or None,
            "email": email or None,
            "phone": phone or None,
            "address": address or None,
            "postcode": postcode or None,
            "lat": (geo or {}).get("lat"),
            "lon": (geo or {}).get("lon"),
            "country": "ENG",  # NCS is England; leave null otherwise
            "provider_type": None,
            "is_residential": 0,
            "is_specialist": 0,
            "s41_approved": 0,
            "ofsted_urn": None,
            "ofsted_url": None,
            "source_flags": json.dumps({"ncs": True}),
            "first_seen_utc": now,
            "last_seen_utc": now
        }
        print("REC",rec)
        upsert_provider(conn, rec)
    conn.commit()
    print("NCS import complete.")

if __name__ == "__main__":
    #url = os.environ.get("NCS_LIVE_PROVIDERS_CSV") or (NCS_LIVE_PROVIDERS_CSV or "").strip()
    from get_latest_ncs_url import get_latest_ncs_csv_url
    print(" NCS LIVE ", os.environ.get("NCS_LIVE_PROVIDERS_CSV"))
    url = os.environ.get("NCS_LIVE_PROVIDERS_CSV") or get_latest_ncs_csv_url()
    print("URL=",url)
    if not url:
        raise SystemExit("Set NCS_LIVE_PROVIDERS_CSV to the 'Live course providers' CSV URL from the NCS page.")
    run(url)
