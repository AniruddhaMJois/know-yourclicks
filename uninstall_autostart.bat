@echo off
REM KnowYourClicks Windows - Uninstall Autostart
cd /d "%~dp0"

echo Removing KnowYourClicks from Windows Autostart...
python knowyourclicks.py autostart-uninstall
echo.
pause
