@echo off@echo off
cd /d "%~dp0"
py -m streamlit run "%~dp0app.py"
pause