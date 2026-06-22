@echo off
title Angetic Essence Command Center
cd /d "%~dp0"
set PYTHON_CMD=python
if exist .venv\Scripts\python.exe (
    set PYTHON_CMD=.venv\Scripts\python.exe
) else (
    where python >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        where py >nul 2>&1
        if %ERRORLEVEL% eq 0 (
            set PYTHON_CMD=py
        )
    )
)
%PYTHON_CMD% launcher.py
pause
