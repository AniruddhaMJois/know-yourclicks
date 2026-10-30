@echo off
REM KnowYourClicks Windows - Install Autostart
cd /d "%~dp0"

echo ========================================================
echo  Configure KnowYourClicks Autostart (Windows)
echo ========================================================
echo.

python knowyourclicks.py autostart-install
echo.
pause
