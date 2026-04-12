@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 AI 视觉处理工具集...
J:\Ai_visual_processing_tools\.venv\Scripts\python.exe toolkit_launcher.py
pause
