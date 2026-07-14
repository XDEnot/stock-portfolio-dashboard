@echo off
title Portfolio Dashboard
echo ===================================================
echo Starting Stock Portfolio Dashboard...
echo ===================================================
echo.
echo Please wait while the application loads in your browser...

call venv\Scripts\activate
streamlit run app.py

pause
