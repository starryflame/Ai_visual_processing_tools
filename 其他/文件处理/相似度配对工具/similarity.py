#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像相似度匹配 - 基于感知哈希 + 颜色直方图
"""

import os
from PIL import Image


def _compute_phash(img):
    """计算感知哈希 (dHash)"""
    img = img.convert('L').resize((18, 8), Image.LANCZOS)
    pixels = list(img.getdata())
    pixels = [pixels[i:i + 18] for i in range(0, len(pixels), 18)]
    diff = []
    for row in pixels:
        for i in range(len(row) - 1):
            diff.append(row[i] > row[i + 1])
    return diff


def _compute_color_hist(img, bins=(8, 8, 4)):
    """计算归一化颜色直方图"""
    img = img.convert('RGB').resize((64, 64))
    hist = []
    for channel in range(3):
        c = img.split()[channel]
        pixels = list(c.getdata())
        bin_counts = [0] * bins[channel]
        for p in pixels:
            idx = min(p // (256 // bins[channel]), bins[channel] - 1)
            bin_counts[idx] += 1
        total = sum(bin_counts) or 1
        hist.append([c / total for c in bin_counts])
    return hist


def _hist_chisquare(h1, h2):
    """计算两个直方图之间的卡方距离"""
    distance = 0.0
    for b1, b2 in zip(h1, h2):
        for v1, v2 in zip(b1, b2):
            if v1 + v2 > 0:
                distance += (v1 - v2) ** 2 / (v1 + v2)
    return distance


def compute_features(img_or_path):
    """计算图片的特征（感知哈希 + 颜色直方图）"""
    if isinstance(img_or_path, str):
        img = Image.open(img_or_path)
    else:
        img = img_or_path
    return _compute_phash(img), _compute_color_hist(img)


def similarity_score(features_a, features_b):
    """计算两张图片的相似度分数（0-1，越高越相似）"""
    phash_a, hist_a = features_a
    phash_b, hist_b = features_b

    # dHash 汉明距离 (0-1, 越小越相似)
    hamming = sum(a != b for a, b in zip(phash_a, phash_b))
    phash_sim = 1.0 - hamming / len(phash_a)

    # 颜色直方图卡方距离 → 归一化相似度
    chi2 = _hist_chisquare(hist_a, hist_b)
    color_sim = 1.0 / (1.0 + chi2)

    return 0.65 * phash_sim + 0.35 * color_sim


def find_best_match(left_img_path, right_folder):
    """在右侧文件夹中找到与左图最相似的图片路径"""
    from config import IMAGE_EXTENSIONS

    best_path = None
    best_score = -1

    left_features = compute_features(left_img_path)

    for fname in os.listdir(right_folder):
        ext = os.path.splitext(fname)[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue
        fpath = os.path.join(right_folder, fname)
        try:
            right_features = compute_features(fpath)
            score = similarity_score(left_features, right_features)
            if score > best_score:
                best_score = score
                best_path = fpath
        except Exception:
            continue

    return best_path, best_score
