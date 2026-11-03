@echo off
title Copy EstateHawk data to Neon
cd /d "%~dp0\.."
echo This copies your local EstateHawk data (leads, contacts, notes, users) into the Neon database.
echo Paste the Neon connection string (starts with postgresql://) and press Enter:
set /p DATABASE_URL=
call ".venv\Scripts\activate.bat"
python -m pip install -q --disable-pip-version-check -r requirements.txt
python deploy\sqlite_to_pg.py data\estatehawk.db
echo.
echo Done. You can close this window.
pause
