@echo off
REM KnowYourClicks Windows - Stop Service
cd /d "%~dp0"

echo Stopping KnowYourClicks background service...
where python.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    python.exe knowyourclicks.py stop
) else (
    where pythonw.exe >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        pythonw.exe knowyourclicks.py stop
    ) else (
        echo [ERROR] Python not found.
    )
)
echo.
pause
