#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""QwenImage 图像生成器 - 启动脚本"""

import subprocess
import sys

if __name__ == "__main__":
    print("🎨 Qwen-Image 图像生成器")
    print("=" * 40)
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "其他/comfyui/web_ui/QwenImage_Generator.py",
        "--server.port=8503",
        "--server.address=127.0.0.1"
    ])
