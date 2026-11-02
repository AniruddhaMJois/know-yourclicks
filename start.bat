@echo off
REM KnowYourClicks Windows - Start Launcher
title KnowYourClicks Launcher
cd /d "%~dp0"

echo ========================================================
echo  KnowYourClicks (Windows)
echo  Privacy-First Keystroke Analytics and Speed Monitor
echo ========================================================
echo.

where pythonw.exe >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    pythonw.exe knowyourclicks.py app
) else (
    where python.exe >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        python.exe knowyourclicks.py app
    ) else (
        echo [ERROR] Python was not found in your PATH.
        echo Please install Python 3 from https://www.python.org/ or the Microsoft Store.
        pause
    )
)
