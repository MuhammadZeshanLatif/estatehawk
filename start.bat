@echo off
title EstateHawk
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer is needed. Download: https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^)
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo First run: setting up... ^(1-2 minutes^)
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install -q --disable-pip-version-check -r requirements.txt
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo  EstateHawk is running at http://localhost:8000
echo  Keep this window open (minimize it). Daily county sync runs while it is open.
echo.
if /i not "%~1"=="silent" start "" http://localhost:8000
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
if /i not "%~1"=="silent" pause
