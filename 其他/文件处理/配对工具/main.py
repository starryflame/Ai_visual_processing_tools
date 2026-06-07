#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双面板图片配对工具 - 主入口
"""

import os
import configparser
import tkinter as tk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from config import DARK_BG
from gui import ImagePairToolGUI


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    # 配置文件与 main.py 同目录
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")
    if os.path.exists(config_path):
        config.read(config_path, encoding='utf-8')
    else:
        # 使用默认配置
        config['MODEL'] = {
            'model_name': 'qwen/qwen3.5-27b',
            'api_base_url': 'http://127.0.0.1:1234/v1',
            'api_key': 'ollama',
            'max_new_tokens': '256',
            'temperature': '0.3',
            'top_p': '0.9',
        }
        config['AI_MATCH'] = {
            'image_max_size': '720',
            'max_attempts': '3',
        }
    return config


def main():
    """主函数"""
    config = load_config()

    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()

    root.config(bg=DARK_BG)

    app = ImagePairToolGUI(root, config=config)
    root.mainloop()


if __name__ == "__main__":
    main()
