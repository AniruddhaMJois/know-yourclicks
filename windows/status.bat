@echo off
REM KnowYourClicks Windows - Status Check
cd /d "%~dp0"

echo ========================================================
echo  KnowYourClicks (Windows) Status
echo ========================================================
echo.

python knowyourclicks.py status
echo.
python knowyourclicks.py stats
echo.
pause
