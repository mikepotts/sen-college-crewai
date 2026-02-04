
# SEN College Finder – FastAPI Backend (Skeleton)

## Setup (Windows)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
notepad .env   # set USER_POSTCODE etc.
```

## Run the API
```powershell
powershell -ExecutionPolicy Bypass -File run_api.ps1
```
Open http://localhost:8000/docs

### Endpoints
- GET /health
- GET /instant?postcode=LS1%201AA&target_count=10
- POST /deep-dive  { "provider_id": "leeds_city_college_printworks" }
