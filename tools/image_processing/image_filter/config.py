#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片过滤工具 - 配置文件
"""

# 深色模式配色方案
DARK_BG = "#2b2b2b"
DARK_FG = "#ffffff"
DARK_ENTRY_BG = "#3c3c3c"
DARK_BUTTON_BG = "#4a4a4a"
DARK_BUTTON_FG = "#ffffff"
DARK_CONTAINER_BG = "#1e1e1e"
DARK_HIGHLIGHT = "#0078d4"

# 结果颜色
RESULT_YES_BG = "#2d7a3e"       # "是" - 绿色
RESULT_NO_BG = "#8b3a3a"        # "不是" - 红色
RESULT_PENDING_BG = "#4a4a4a"   # 待判断 - 灰色
RESULT_MANUAL_YES_BG = "#1a6b8a"  # 手动确认 - 蓝色

# 图片文件扩展名
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']

# 窗口默认尺寸
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 850

# 图片展示区域默认高度
IMAGE_AREA_HEIGHT = 600

# 预设筛选条件
PRESET_CONDITIONS = [
    "背景是简单纯色（白色、黑色、灰色等单一颜色）",
    "背景是自然风景（天空、草地、森林、海洋等）",
    "背景是室内场景（房间、工作室、棚拍等）",
    "图片中包含文字/水印/Logo",
    "图片是二次元/动漫风格",
    "图片是真人照片",
]
