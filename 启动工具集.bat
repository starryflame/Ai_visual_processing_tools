@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 未找到虚拟环境: "%~dp0.venv"
    echo 请先在本目录执行:  uv sync
    pause
    exit /b 1
)

".venv\Scripts\python.exe" toolkit_launcher.py
