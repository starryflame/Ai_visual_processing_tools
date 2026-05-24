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
            - 'top': 竖图裁剪上面（保留顶部），横图居中
            - 'bottom': 竖图裁剪下面（保留底部），横图居中

    Returns:
        裁剪后的正方形图片
    """
    width, height = img.size
    size = min(width, height)

    if width == height:
        return img.copy()

    if width > height:
        # 横图：从中间裁剪
        left = (width - height) // 2
        top = 0
        right = left + size
        bottom = height
    else:
        # 竖图
        left = 0
        right = size
        if crop_style == 'bottom':
            top = height - size
            bottom = height
        else:
            top = 0
            bottom = size

    return img.crop((left, top, right, bottom))


def generate_renamed_filename(original_name, index, total_count):
    """根据索引生成新的文件名（pair_001.jpg, pair_002.jpg...）"""
    from pathlib import Path
    name_part = Path(original_name).stem
    ext_part = Path(original_name).suffix
    # 使用三位序号，如 001, 002, ...
    new_name = f"pair_{index:03d}{ext_part}"
    return new_name


def stitch_pair_preview(img_left, img_right, bg_color=(255, 255, 255)):
    """拼接左右图到接近正方形的预览图。
    横图→纵向拼接, 竖图→横向拼接, 混排自动选更优方案。
    """
    w1, h1 = img_left.size
    w2, h2 = img_right.size

    both_landscape = w1 >= h1 and w2 >= h2
    both_portrait = h1 > w1 and h2 > w2

    # 横向拼接 (side by side) 的宽高比
    w_side = w1 + w2
    h_side = max(h1, h2)
    side_ratio = max(w_side, h_side) / min(w_side, h_side) if min(w_side, h_side) > 0 else float('inf')

    # 纵向拼接 (stacked) 的宽高比
    w_stack = max(w1, w2)
    h_stack = h1 + h2
    stack_ratio = max(w_stack, h_stack) / min(w_stack, h_stack) if min(w_stack, h_stack) > 0 else float('inf')

    if both_landscape:
        mode = 'vertical'
    elif both_portrait:
        mode = 'horizontal'
    else:
        mode = 'horizontal' if side_ratio <= stack_ratio else 'vertical'

    if mode == 'horizontal':
        result = Image.new('RGB', (w_side, h_side), bg_color)
        result.paste(img_left, (0, (h_side - h1) // 2))
        result.paste(img_right, (w1, (h_side - h2) // 2))
    else:
        result = Image.new('RGB', (w_stack, h_stack), bg_color)
        result.paste(img_left, ((w_stack - w1) // 2, 0))
        result.paste(img_right, ((w_stack - w2) // 2, h1))

    return result


def get_image_files(folder_path):
    """获取文件夹中的所有图片文件"""
    from pathlib import Path
    import os
    from config import IMAGE_EXTENSIONS

    if not folder_path or not os.path.exists(folder_path):
        return []

    return [f for f in os.listdir(folder_path)
            if Path(f).suffix.lower() in IMAGE_EXTENSIONS]
