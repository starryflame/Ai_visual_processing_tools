#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双面板图片配对工具 - AI 人物判断模块
通过调用 LLM 视觉模型判断两张图片中的人物是否是同一个人
"""

import os
import io
import re
import base64
import configparser
import logging
import threading
import shutil
from pathlib import Path

from PIL import Image
from openai import OpenAI

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 判断结果映射
RESULT_LABELS = {
    "完全不是": "not_same",
    "有些像": "somewhat_similar",
    "肯定就是": "definitely_same",
}

# 输出文件夹名称（"完全不是"不创建文件夹，直接跳过）
OUTPUT_FOLDERS = {
    "有些像": "有些像",
    "肯定就是": "肯定就是",
}

# 默认人物判断提示词
DEFAULT_MATCH_PROMPT = (
    "你是一个专业的人物判断助手,你会看到两张cosplay图片,然后判断两张图片里的cos的人物是不是同一个,"
    "仅输出以下三个置信度模板回答,\n"
    "完全不是\n"
    "有些像\n"
    "肯定就是\n"
    ",不要输出其他描述性还有解释性的内容,由于二次元角色的 cosplay 图大概率人脸是不相同的,"
    "因为coser会是不同的人,可能甚至衣服也不会相同,因为一个角色他可能有多套服装,"
    "你需要关注一些明显的相同关键点,例如，关注他们的发色,发型,眼睛,"
    "还有相同的特殊装饰物品,例如头顶光环,尾巴等"
)


class LLMClient:
    """LLM API 客户端封装类，通过 OpenAI 兼容 API 格式调用 AI 服务"""

    def __init__(self, config):
        """初始化客户端

        Args:
            config: configparser.ConfigParser 对象，包含配置信息
        """
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化 OpenAI 客户端（兼容任何 OpenAI API 格式的服务）"""
        api_base_url = self.config.get('MODEL', 'api_base_url', fallback='http://127.0.0.1:1234/v1')
        api_key = self.config.get('MODEL', 'api_key', fallback='ollama')

        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base_url,
            timeout=3600
        )

    def get_model_config(self):
        """获取模型和生成参数配置

        Returns:
            tuple: (model_name, max_new_tokens, temperature, top_p)
        """
        model_name = self.config.get('MODEL', 'model_name', fallback='qwen3-vl:30b')
        max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=256)
        temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.3)
        top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)

        return model_name, max_new_tokens, temperature, top_p

    def convert_image_to_base64(self, image_path):
        """将图片文件转换为 base64 编码

        Args:
            image_path: 图片文件路径

        Returns:
            str: base64 编码的 data URL
        """
        max_size = self.config.getint('AI_MATCH', 'image_max_size', fallback=720)

        image = Image.open(image_path)
        # 转换为 RGB（处理 RGBA / P 等模式）
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{encoded}"

        return data_url

    def match_person(self, left_image_path, right_image_path, prompt_text=None, max_attempts=3):
        """调用 AI 模型判断两张图片中的人物是否是同一个人

        Args:
            left_image_path: 左侧图片路径
            right_image_path: 右侧图片路径
            prompt_text: 自定义提示词，默认使用人物判断提示词
            max_attempts: 最大重试次数

        Returns:
            str: 判断结果，值为 "完全不是"、"有些像"、"肯定就是" 之一
                 如果解析失败，返回 None
        """
        if prompt_text is None:
            prompt_text = DEFAULT_MATCH_PROMPT

        # 转换两张图片为 base64
        left_data_url = self.convert_image_to_base64(left_image_path)
        right_data_url = self.convert_image_to_base64(right_image_path)

        # 构造消息内容
        content_list = [
            {
                "type": "text",
                "text": prompt_text
            },
            {
                "type": "image_url",
                "image_url": {"url": left_data_url}
            },
            {
                "type": "image_url",
                "image_url": {"url": right_data_url}
            }
        ]

        messages = [{"role": "user", "content": content_list}]

        # 获取配置参数
        model_name, max_new_tokens, temperature, top_p = self.get_model_config()

        # 有效的判断结果
        valid_results = list(RESULT_LABELS.keys())

        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )

                caption = response.choices[0].message.content.strip()

                # 过滤掉模型输出的思考过程 (<think> ... </think>)
                thought_pattern = r"<think>.*?</think>"
                cleaned_caption = re.sub(thought_pattern, "", caption, flags=re.DOTALL | re.IGNORECASE).strip()

                if cleaned_caption:
                    caption = cleaned_caption
                elif "</think>" in caption:
                    parts = caption.split("</think>")
                    if len(parts) > 1:
                        caption = parts[-1].strip()

                # 匹配结果
                for result_label in valid_results:
                    if result_label in caption:
                        logger.info(f"匹配结果: {result_label}")
                        return result_label

                # 如果没有匹配到有效结果，记录并重试
                logger.warning(f"未能从回复中解析出有效结果 (尝试 {attempt + 1}/{max_attempts}): {caption[:100]}...")
                if attempt < max_attempts - 1:
                    continue

            except Exception as e:
                logger.error(f"API 调用失败 (尝试 {attempt + 1}/{max_attempts}): {str(e)}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    raise

        # 所有重试完成但无法解析，返回 None
        logger.warning(f"经过 {max_attempts} 次尝试后仍无法解析结果")
        return None


def run_ai_person_match(left_image_path, right_folder, output_base_folder,
                        config, status_callback=None, progress_callback=None,
                        should_cancel=None):
    """在后台线程中执行 AI 人物判断匹配

    遍历右侧文件夹中的所有图片，依次与左侧选中的图片进行 AI 比对，
    根据结果将右图复制到对应的分类文件夹中。

    Args:
        left_image_path: 左侧选中的图片路径（参照图）
        right_folder: 右侧图片文件夹路径
        output_base_folder: 输出根目录（会在其下创建"完全不是"/"有些像"/"肯定就是"子文件夹）
        config: configparser.ConfigParser 对象
        status_callback: 状态更新回调函数，接收 (text: str)
        progress_callback: 进度更新回调函数，接收 (current: int, total: int)
        should_cancel: 取消检查回调函数，返回 True 表示取消，默认 None 表示不取消

    Returns:
        dict: 结果统计 {"完全不是": count, "有些像": count, "肯定就是": count, "errors": [str]}
    """
    from utils import get_image_files

    # 获取右侧所有图片文件
    right_images = get_image_files(right_folder)
    if not right_images:
        if status_callback:
            status_callback("右侧文件夹中没有图片文件")
        return None

    right_images.sort()
    total = len(right_images)

    # 创建输出子文件夹
    output_folders = {}
    for label, folder_name in OUTPUT_FOLDERS.items():
        folder_path = os.path.join(output_base_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        output_folders[label] = folder_path

    # 将参考图复制到输出根目录
    left_name = Path(left_image_path).name
    ref_dest = _get_unique_filename(output_base_folder, left_name)
    shutil.copy2(left_image_path, ref_dest)
    logger.info(f"参考图已复制: {left_name} -> {ref_dest}")

    # 初始化 LLM 客户端
    llm_client = LLMClient(config)

    max_attempts = config.getint('AI_MATCH', 'max_attempts', fallback=3)

    # 统计
    results = {
        "完全不是": 0,
        "有些像": 0,
        "肯定就是": 0,
        "errors": [],
        "unmatched": 0,
    }

    left_name = Path(left_image_path).name

    for i, right_filename in enumerate(right_images):
        # 检查是否取消
        if should_cancel and should_cancel():
            if status_callback:
                status_callback("已取消 AI 判断")
            results["_cancelled"] = True
            return results

        right_path = os.path.join(right_folder, right_filename)
        right_name = right_filename

        # 更新状态
        if status_callback:
            status_callback(f"正在判断 ({i + 1}/{total}): {left_name} vs {right_name}")

        try:
            # 调用 AI 判断
            result_label = llm_client.match_person(
                left_image_path, right_path,
                max_attempts=max_attempts
            )

            if result_label is not None and result_label in output_folders:
                # 复制右图到对应分类文件夹
                dest_folder = output_folders[result_label]
                dest_path = _get_unique_filename(dest_folder, right_name)
                shutil.copy2(right_path, dest_path)
                results[result_label] += 1
                logger.info(f"[{result_label}] {right_name} -> {dest_folder}")
            elif result_label == "完全不是":
                # 完全不是：不复制，仅计数
                results["完全不是"] += 1
                logger.info(f"[完全不是] {right_name} -> 跳过")
            else:
                # 无法判断的图像复制到"有些像"文件夹（保守处理）
                dest_folder = output_folders["有些像"]
                dest_path = _get_unique_filename(dest_folder, right_name)
                shutil.copy2(right_path, dest_path)
                results["有些像"] += 1
                results["unmatched"] += 1
                logger.warning(f"[无法判断，归入有些像] {right_name}")

        except Exception as e:
            error_msg = f"{right_name}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(f"处理 {right_name} 时出错: {str(e)}")

        # 更新进度
        if progress_callback:
            progress_callback(i + 1, total)

    # 完成提示
    if status_callback:
        summary = (
            f"AI 判断完成！"
            f" 完全不是: {results['完全不是']} | "
            f"有些像: {results['有些像']} | "
            f"肯定就是: {results['肯定就是']}"
        )
        if results["errors"]:
            summary += f" | 错误: {len(results['errors'])}"
        status_callback(summary)

    return results


def _get_unique_filename(folder, filename):
    """在目标文件夹中生成不重复的文件名

    Args:
        folder: 目标文件夹路径
        filename: 原始文件名

    Returns:
        str: 不重复的完整文件路径
    """
    base_path = os.path.join(folder, filename)
    if not os.path.exists(base_path):
        return base_path

    name, ext = os.path.splitext(filename)
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        new_path = os.path.join(folder, new_name)
        if not os.path.exists(new_path):
            return new_path
        counter += 1


def _make_pair_key(name_a, name_b):
    """生成对称的配对键，确保 (A,B) 和 (B,A) 得到相同键值"""
    if name_a < name_b:
        return (name_a, name_b)
    return (name_b, name_a)


def run_ai_person_match_batch(left_folder, right_folder, output_base_folder,
                               config, status_callback=None, progress_callback=None,
                               should_cancel=None):
    """批量 AI 人物判断：左侧每张图依次作为参照图，与右侧所有图比对。

    遍历左侧文件夹中的所有图片，每张作为参照图与右侧所有图片进行 AI 比对。
    使用对称配对缓存避免重复判断：(A,B) 和 (B,A) 只调用一次 AI。

    Args:
        left_folder: 左侧图片文件夹路径
        right_folder: 右侧图片文件夹路径
        output_base_folder: 输出根目录
        config: configparser.ConfigParser 对象
        status_callback: 状态更新回调函数，接收 (text: str)
        progress_callback: 进度更新回调函数，接收 (current: int, total: int)
        should_cancel: 取消检查回调函数，返回 True 表示取消

    Returns:
        dict: 结果统计
    """
    from utils import get_image_files

    # 获取左右两侧所有图片文件
    left_images = get_image_files(left_folder)
    right_images = get_image_files(right_folder)

    if not left_images:
        if status_callback:
            status_callback("左侧文件夹中没有图片文件")
        return None
    if not right_images:
        if status_callback:
            status_callback("右侧文件夹中没有图片文件")
        return None

    left_images.sort()
    right_images.sort()

    total_left = len(left_images)
    total_right = len(right_images)

    # 初始化 LLM 客户端
    llm_client = LLMClient(config)
    max_attempts = config.getint('AI_MATCH', 'max_attempts', fallback=3)

    # 对称配对缓存：key=(name_a, name_b) sorted, value=result_label
    pair_cache = {}

    # 统计
    total_results = {
        "完全不是": 0,
        "有些像": 0,
        "肯定就是": 0,
        "errors": [],
        "unmatched": 0,
        "cached": 0,       # 命中缓存的次数
        "skipped_self": 0, # 跳过的自身对比
    }

    # 计算总任务数（用于进度条）
    total_pairs = total_left * total_right
    completed = 0

    for li, left_filename in enumerate(left_images):
        left_path = os.path.join(left_folder, left_filename)
        left_stem = Path(left_filename).stem

        # 检查取消
        if should_cancel and should_cancel():
            if status_callback:
                status_callback("已取消批量 AI 判断")
            total_results["_cancelled"] = True
            return total_results

        # 为当前左图创建输出子文件夹
        left_output = os.path.join(output_base_folder, left_stem)
        os.makedirs(left_output, exist_ok=True)

        # 复制参考图
        ref_dest = _get_unique_filename(left_output, left_filename)
        shutil.copy2(left_path, ref_dest)

        # 创建置信度子文件夹
        left_output_folders = {}
        for label, folder_name in OUTPUT_FOLDERS.items():
            folder_path = os.path.join(left_output, folder_name)
            os.makedirs(folder_path, exist_ok=True)
            left_output_folders[label] = folder_path

        if status_callback:
            status_callback(f"参照图 ({li + 1}/{total_left}): {left_filename}")

        for ri, right_filename in enumerate(right_images):
            # 检查取消
            if should_cancel and should_cancel():
                if status_callback:
                    status_callback("已取消批量 AI 判断")
                total_results["_cancelled"] = True
                return total_results

            completed += 1
            if progress_callback:
                progress_callback(completed, total_pairs)

            right_path = os.path.join(right_folder, right_filename)

            # 同一张图跳过
            if left_path == right_path:
                total_results["skipped_self"] += 1
                continue

            # 检查对称缓存
            pair_key = _make_pair_key(left_filename, right_filename)
            if pair_key in pair_cache:
                result_label = pair_cache[pair_key]
                total_results["cached"] += 1
            else:
                # 调用 AI 判断
                if status_callback:
                    status_callback(
                        f"AI判断 ({li + 1}/{total_left}): {left_filename} vs {right_filename} "
                        f"({completed}/{total_pairs})"
                    )

                try:
                    result_label = llm_client.match_person(
                        left_path, right_path,
                        max_attempts=max_attempts
                    )
                except Exception as e:
                    error_msg = f"{left_filename} vs {right_filename}: {str(e)}"
                    total_results["errors"].append(error_msg)
                    logger.error(error_msg)
                    continue

                # 存入缓存
                pair_cache[pair_key] = result_label

            # 根据结果处理
            if result_label is not None and result_label in left_output_folders:
                dest_folder = left_output_folders[result_label]
                dest_path = _get_unique_filename(dest_folder, right_filename)
                shutil.copy2(right_path, dest_path)
                total_results[result_label] += 1
            elif result_label == "完全不是":
                total_results["完全不是"] += 1
                # 不复制，跳过
            else:
                # 无法判断 → 归入"有些像"
                dest_folder = left_output_folders["有些像"]
                dest_path = _get_unique_filename(dest_folder, right_filename)
                shutil.copy2(right_path, dest_path)
                total_results["有些像"] += 1
                total_results["unmatched"] += 1

    # 完成提示
    if status_callback:
        cache_hit = total_results["cached"]
        skipped = total_results["skipped_self"]
        summary = (
            f"批量AI判断完成！"
            f" 完全不是: {total_results['完全不是']} | "
            f"有些像: {total_results['有些像']} | "
            f"肯定就是: {total_results['肯定就是']}"
        )
        if cache_hit > 0:
            summary += f" | 缓存命中: {cache_hit}"
        if skipped > 0:
            summary += f" | 跳过自身: {skipped}"
        if total_results["errors"]:
            summary += f" | 错误: {len(total_results['errors'])}"
        status_callback(summary)

    return total_results
