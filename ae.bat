@echo off
set AE_DEV_MODE=true
title Angetic Essence — User Mode
cd /d "%~dp0"

echo ============================================================
echo   ANGETIC ESSENCE — Launching
echo ============================================================
echo.

set PYTHON_CMD=py
if exist .venv\Scripts\python.exe (
    set PYTHON_CMD=.venv\Scripts\python.exe
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% eq 0 (
        set PYTHON_CMD=python
    )
)

%PYTHON_CMD% -c "from core.licensing import validate_or_exit; validate_or_exit()" 2>nul
if %ERRORLEVEL% neq 0 (
    echo.
    echo LICENSE ERROR: Please set a valid license key in config.yaml
    echo.
    pause
    exit /b 1
)

echo [OK] License validated
echo [OK] Starting agent engine...
start "AE Engine" /MIN %PYTHON_CMD% main.py

echo [OK] Starting dashboard...
start "AE Dashboard" /MIN %PYTHON_CMD% dashboard\app.py

timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000

echo.
echo ============================================================
echo   Angetic Essence is running
echo   Dashboard : http://127.0.0.1:5000
echo   Login     : admin / essence2024
echo ============================================================
echo.
echo Close this window to shut down all components.
pause

echo Shutting down...
taskkill /f /im python.exe >nul 2>&1
exit
