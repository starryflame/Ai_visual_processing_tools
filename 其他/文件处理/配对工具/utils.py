#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双面板图片配对工具 - 工具函数
"""

from PIL import Image


def fill_image_with_background(img, target_size, bg_color=(255, 255, 255)):
    """将图片居中放置到指定尺寸的白色背景上"""
    target_w, target_h = target_size

    # 创建带 Alpha 通道的图像用于计算
    img_rgba = img.convert('RGBA')
    width, height = img.size

    # 计算缩放比例，确保图片完整显示在目标区域内（保持宽高比）
    scale = min(target_w / width, target_h / height)
    new_width = int(width * scale)
    new_height = int(height * scale)

    # 缩放图片
    img_resized = img.resize((new_width, new_height), Image.LANCZOS)

    # 创建白色背景图像
    background = Image.new('RGBA', (target_w, target_h), bg_color + (255,))

    # 计算居中位置
    paste_x = (target_w - new_width) // 2
    paste_y = (target_h - new_height) // 2

    # 将缩放后的图片粘贴到背景中央
    background.paste(img_resized, (paste_x, paste_y), img_resized if img.mode == 'RGBA' else None)

    return background.convert('RGB')


def generate_renamed_filename(original_name, index, total_count):
    """根据索引生成新的文件名（pair_001.jpg, pair_002.jpg...）"""
    from pathlib import Path
    name_part = Path(original_name).stem
    ext_part = Path(original_name).suffix
    # 使用三位序号，如 001, 002, ...
    new_name = f"pair_{index:03d}{ext_part}"
    return new_name


def get_image_files(folder_path):
    """获取文件夹中的所有图片文件"""
    from pathlib import Path
    import os
    from config import IMAGE_EXTENSIONS

    if not folder_path or not os.path.exists(folder_path):
        return []

    return [f for f in os.listdir(folder_path)
            if Path(f).suffix.lower() in IMAGE_EXTENSIONS]
