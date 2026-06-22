@echo off
title Angetic Essence — SaaS Setup
echo ========================================
echo   ANGETIC ESSENCE — SaaS Platform Setup
echo ========================================
echo.
echo Installing dependencies...
pip install -r "%~dp0requirements.txt"
pip install flask flask-cors
echo.
echo Setup complete!
echo.
echo To launch the Command Center:
echo   double-click launcher.bat
echo.
pause
