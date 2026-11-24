@echo off
echo ===================================================
echo   Starting RainVision Machine Learning Web Platform
echo ===================================================
echo.
cd /d "%~dp0website"
echo Launching Flask Application on http://localhost:5000 ...
python app.py
pause

