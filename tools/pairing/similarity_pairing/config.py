#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""相似度配对工具 - 配置文件"""

import os

DARK_BG = "#2b2b2b"
DARK_FG = "#ffffff"
DARK_ENTRY_BG = "#3c3c3c"
DARK_BUTTON_BG = "#4a4a4a"
DARK_BUTTON_FG = "#ffffff"
DARK_CONTAINER_BG = "#1e1e1e"
DARK_HIGHLIGHT = "#0078d4"

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif', '.tiff'}

WINDOW_WIDTH = 1560
WINDOW_HEIGHT = 840
IMAGE_AREA_HEIGHT = 430
IMAGE_AREA_WIDTH = 520

# 去重：1200 bit 2D dHash 中差异不超过该位数视为同一张硬线条图。
# 实测重编码/缩放副本差异 ≤10 bit，不同构图的硬线条图相差 350 bit 以上，
# 20 bit（约 1.7%）仍然非常严格。
DEDUPE_MAX_BITS = 20
# 匹配结果的最低保留分（为了允许事后调低阈值，先保留到该分数）
MATCH_FLOOR = 0.45
# 一对多导出时的默认相似度阈值。
# 在 260 对真实动漫→真人数据上：0.68 ≈ 精确率 99.5% / 召回 82.7%；
# 调到 0.67 约为 96.1% / 85.8%，按需要取舍。
DEFAULT_MATCH_THRESHOLD = 0.68
# 右侧特征缓存文件（跨会话复用）
CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '.cache', 'features.pkl'
)

# 特征提取并行度。解码/PIL/numpy 的大部分工作在 C 层且会释放 GIL，
# 用线程就能吃满多核，并额外利用磁盘 I/O 等待；不需要进程池。
FEATURE_WORKERS = max(4, min(8, os.cpu_count() or 4))
