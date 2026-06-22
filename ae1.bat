@echo off
set AE_DEV_MODE=true
title Angetic Essence — Owner Mode (AE1)
cd /d "%~dp0"

echo ============================================================
echo   ANGETIC ESSENCE — OWNER DEPLOYMENT
echo   Watchdog + License Server + Dashboard
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

echo [1/4] Checking license server keys...
if not exist "license_server\keys\private.pem" (
    %PYTHON_CMD% -c "from license_server.crypto import generate_key_pair; generate_key_pair(); print('[OK] RSA key pair generated')"
) else (
    echo [OK] RSA key pair exists
)

echo [2/4] Starting license server (port 8080)...
start "AE License Server" %PYTHON_CMD% -m license_server.app

echo [3/4] Starting watchdog...
start "AE Watchdog" %PYTHON_CMD% watchdog.py

echo [4/4] Starting dashboard...
start "AE Dashboard" %PYTHON_CMD% dashboard\app.py

timeout /t 4 /nobreak >nul
start http://127.0.0.1:5000
start http://127.0.0.1:8080/health

echo.
echo ============================================================
echo   AE1 — OWNER MODE ACTIVE
echo   Dashboard     : http://127.0.0.1:5000
echo   License API   : http://127.0.0.1:8080
echo   Login         : admin / essence2024
echo   Watchdog      : monitors main.py, auto-rollback on crash
echo ============================================================
echo.
echo Close this window OR press any key to shut down the entire stack.
pause

echo.
echo Shutting down all AE components...
taskkill /f /fi "WINDOWTITLE eq AE License Server" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq AE Watchdog" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq AE Dashboard" >nul 2>&1
taskkill /f /fi "WINDOWTITLE eq AE Engine" >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
echo Done.
timeout /t 2 /nobreak >nul
exit
