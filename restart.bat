@echo off
title EH restart
cd /d "%~dp0"
echo Stopping old EstateHawk server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>nul
timeout /t 2 /nobreak >nul
echo Starting new EstateHawk...
start "EstateHawk" cmd /c start.bat
exit
