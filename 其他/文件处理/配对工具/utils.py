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


def crop_to_square(img, crop_style='top'):
    """
    将图片裁剪为 1:1 正方形

    Args:
        img: PIL Image 对象
        crop_style: 裁剪方式
            - 'top': 竖图裁剪上面（保留顶部）
            - 'center': 横图裁剪中间（居中裁剪）

    Returns:
        裁剪后的正方形图片
    """
    width, height = img.size
    size = min(width, height)

    if width == height:
        # 已经是正方形，直接返回
        return img.copy()

    if width > height:
        # 横图：从中间裁剪
        left = (width - height) // 2
        top = 0
        right = left + size
        bottom = height
    else:
        # 竖图：裁剪上面（保留顶部）
        left = 0
        top = 0
        right = size
        bottom = top + size

    return img.crop((left, top, right, bottom))


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
