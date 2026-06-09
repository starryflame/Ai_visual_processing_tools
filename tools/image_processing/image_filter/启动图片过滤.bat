@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
".venv\Scripts\python.exe" "tools\image_processing\image_filter\main.py"
pause
