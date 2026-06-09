#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片过滤工具 - 主入口
使用本地大模型识别图片特征，筛选并导出符合条件的图片
"""

import os
import configparser
import tkinter as tk

try:
    from tkinterdnd2 import TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from config import DARK_BG
from gui import ImageFilterGUI


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
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
            'temperature': '0.1',
            'top_p': '0.9',
        }
        config['FILTER'] = {
            'image_max_size': '1024',
            'max_attempts': '2',
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

    app = ImageFilterGUI(root, config=config)
    root.mainloop()


if __name__ == "__main__":
    main()
