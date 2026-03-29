#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Qwen-Image 多模式图像编辑器启动脚本
支持单图、双图、三图三种编辑模式的统一界面

运行方式：
    python run_qwen_edit_multimode.py
或
    streamlit run run_qwen_edit_multimode.py
"""

import subprocess
import sys
import os


def main():
    """启动 Streamlit 应用"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_script = os.path.join(script_dir, "qwen_edit_multimode_app.py")
    
    if not os.path.exists(app_script):
        print(f"错误：未找到应用脚本 {app_script}")
        sys.exit(1)
    
    print("🚀 正在启动 Qwen-Image 多模式图像编辑器...")
    print("=" * 50)
    
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_script])


if __name__ == "__main__":
    main()
