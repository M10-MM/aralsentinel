@echo off
rem Starts AralSentinel at http://localhost:8000 (double-click or run from any terminal)
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    py -m venv .venv
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)
cd ..
start "" http://localhost:8000
backend\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000
