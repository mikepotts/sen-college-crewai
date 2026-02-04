
$env:PYTHONPATH = "$PWD"
.\.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
