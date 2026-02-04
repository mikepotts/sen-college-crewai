from pathlib import Path

DATA_DIR   = Path(__file__).resolve().parents[2] / "data"
DB_PATH    = DATA_DIR / "providers.sqlite"

# Monthly NCS: Live course providers (CSV)
# Latest page (updated monthly) describes links; we read the CSV (December 2025 shown on the page as example; your code will accept a URL env var too):
NCS_LIVE_PROVIDERS_CSV = None  # set via env or CLI arg

# Section 41 (Excel)
S41_XLSX_URL = "https://www.gov.uk/government/publications/independent-special-schools-and-colleges"  # landing (we'll let user provide the direct .xlsx URL)