@echo off
echo ===================================================
echo   Starting RainVision Machine Learning Web Platform
echo ===================================================
echo.
cd /d "%~dp0"
echo [1/2] Checking Python environment...
python --version
echo.
echo [2/2] Launching Flask Application on http://localhost:5000 ...
python app.py
pause

