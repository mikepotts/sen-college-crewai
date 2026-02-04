import sqlite3, json
from pathlib import Path

def get_conn(db_path: Path):
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def ensure_schema(conn: sqlite3.Connection, schema_sql: str):
    conn.executescript(schema_sql)
    conn.commit()

def upsert_provider(conn, rec: dict):
    # provider_id is mandatory
    fields = ["provider_id","ukprn","name","website","email","phone","address","postcode",
              "lat","lon","country","provider_type","is_residential","is_specialist","s41_approved",
              "ofsted_urn","ofsted_url","source_flags","first_seen_utc","last_seen_utc"]
    placeholders = ",".join(["?"]*len(fields))
    update_set = ",".join([f"{f}=excluded.{f}" for f in fields if f not in ("provider_id","first_seen_utc")])
    vals = [rec.get(f) for f in fields]
    conn.execute(f"""
      INSERT INTO providers ({",".join(fields)}) VALUES ({placeholders})
      ON CONFLICT(provider_id) DO UPDATE SET {update_set}
    """, vals)