@echo off
rem Starts EstateHawk quietly (minimized) every time you log in to Windows,
rem so the daily morning county sync always runs. Run this file once.
cd /d "%~dp0"
set "VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\EstateHawk.vbs"
> "%VBS%" echo Set sh = CreateObject("WScript.Shell")
>> "%VBS%" echo sh.CurrentDirectory = "%~dp0"
>> "%VBS%" echo sh.Run """%~dp0start.bat"" silent", 7, False
echo.
echo  Done. EstateHawk will now start by itself (minimized) when Windows starts.
echo  Open it any time at http://localhost:8000
echo  To turn this off, run remove_autostart.bat
echo.
pause
