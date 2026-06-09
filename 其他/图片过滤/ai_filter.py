#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片过滤工具 - AI 筛选模块
通过调用本地 LLM 视觉模型判断图片是否满足用户指定的条件
"""

import os
import io
import re
import base64
import configparser
import logging

from PIL import Image
from openai import OpenAI

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def build_filter_prompt(condition_text):
    """构建筛选提示词

    Args:
        condition_text: 用户输入的筛选条件描述

    Returns:
        str: 完整的提示词
    """
    prompt = (
        f"你是一个专业的图片内容判断助手。请仔细观察这张图片，判断是否满足以下条件：\n\n"
        f"条件：{condition_text}\n\n"
        f"请只回答一个字：\n"
        f"- 如果图片满足上述条件，回答：是\n"
        f"- 如果图片不满足上述条件，回答：不是\n\n"
        f"不要输出任何其他解释、描述或标点符号。只输出'是'或'不是'。"
    )
    return prompt


class LLMFilterClient:
    """LLM API 客户端封装类，用于图片筛选"""

    def __init__(self, config):
        """初始化客户端

        Args:
            config: configparser.ConfigParser 对象
        """
        self.config = config
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化 OpenAI 兼容客户端"""
        api_base_url = self.config.get('MODEL', 'api_base_url', fallback='http://127.0.0.1:1234/v1')
        api_key = self.config.get('MODEL', 'api_key', fallback='ollama')

        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base_url,
            timeout=3600
        )

    def get_model_config(self):
        """获取模型和生成参数配置"""
        model_name = self.config.get('MODEL', 'model_name', fallback='qwen3-vl:30b')
        max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=256)
        temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.1)
        top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)

        return model_name, max_new_tokens, temperature, top_p

    def convert_image_to_base64(self, image_path):
        """将图片文件转换为 base64 编码的 data URL"""
        max_size = self.config.getint('FILTER', 'image_max_size', fallback=1024)

        image = Image.open(image_path)
        if image.mode in ('RGBA', 'P'):
            image = image.convert('RGB')
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=85)
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{encoded}"

        return data_url

    def check_image(self, image_path, condition_text, max_attempts=2):
        """判断单张图片是否满足条件

        Args:
            image_path: 图片文件路径
            condition_text: 筛选条件描述
            max_attempts: 最大重试次数

        Returns:
            bool or None: True=是, False=不是, None=无法判断
        """
        prompt_text = build_filter_prompt(condition_text)
        data_url = self.convert_image_to_base64(image_path)

        content_list = [
            {
                "type": "text",
                "text": prompt_text
            },
            {
                "type": "image_url",
                "image_url": {"url": data_url}
            }
        ]

        messages = [{"role": "user", "content": content_list}]

        model_name, max_new_tokens, temperature, top_p = self.get_model_config()

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

                # 过滤掉 <think> 标签
                thought_pattern = r"<think>.*?</think>"
                cleaned = re.sub(thought_pattern, "", caption, flags=re.DOTALL | re.IGNORECASE).strip()

                if cleaned:
                    caption = cleaned
                elif "</think>" in caption:
                    parts = caption.split("</think>")
                    if len(parts) > 1:
                        caption = parts[-1].strip()

                logger.info(f"模型原始回复: '{caption}'")

                # 解析结果
                if '是' in caption and '不是' not in caption:
                    return True
                elif '不是' in caption:
                    return False
                elif caption == '是':
                    return True
                elif caption == '不是':
                    return False
                else:
                    # 尝试更宽松的匹配
                    first_char = caption[0] if caption else ''
                    if first_char == '是':
                        return True
                    elif first_char == '不':
                        return False

                    logger.warning(f"无法解析回复 (尝试 {attempt + 1}/{max_attempts}): '{caption[:100]}'")
                    if attempt < max_attempts - 1:
                        continue

            except Exception as e:
                logger.error(f"API 调用失败 (尝试 {attempt + 1}/{max_attempts}): {str(e)}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    raise

        logger.warning(f"经过 {max_attempts} 次尝试后仍无法解析结果")
        return None


def batch_filter_images(image_folder, condition_text, config,
                        status_callback=None, progress_callback=None,
                        should_cancel=None, on_match_callback=None):
    """批量筛选图片：遍历文件夹中所有图片，用 AI 逐一判断

    Args:
        image_folder: 图片文件夹路径
        condition_text: 筛选条件描述
        config: configparser.ConfigParser 对象
        status_callback: 状态更新回调 (text: str)
        progress_callback: 进度更新回调 (current: int, total: int)
        should_cancel: 取消检查回调，返回 True 表示取消
        on_match_callback: 匹配成功回调 (filename: str, image_path: str)，
                           当 AI 判断为"是"时立即调用，用于即时复制

    Returns:
        dict: {
            "results": [{"filename": str, "path": str, "result": bool|None, "error": str|None}, ...],
            "yes_count": int,
            "no_count": int,
            "error_count": int,
            "_cancelled": bool
        }
    """
    from pathlib import Path
    from config import IMAGE_EXTENSIONS

    # 获取所有图片文件
    image_files = []
    for f in sorted(os.listdir(image_folder)):
        if Path(f).suffix.lower() in IMAGE_EXTENSIONS:
            image_files.append(f)

    if not image_files:
        if status_callback:
            status_callback("文件夹中没有图片文件")
        return None

    total = len(image_files)

    # 初始化 LLM 客户端
    llm_client = LLMFilterClient(config)
    max_attempts = config.getint('FILTER', 'max_attempts', fallback=2)

    results = []
    yes_count = 0
    no_count = 0
    error_count = 0

    for i, filename in enumerate(image_files):
        # 检查取消
        if should_cancel and should_cancel():
            if status_callback:
                status_callback("已取消 AI 筛选")
            return {
                "results": results,
                "yes_count": yes_count,
                "no_count": no_count,
                "error_count": error_count,
                "_cancelled": True
            }

        image_path = os.path.join(image_folder, filename)

        if status_callback:
            status_callback(f"正在判断 ({i + 1}/{total}): {filename}")

        try:
            result = llm_client.check_image(image_path, condition_text, max_attempts=max_attempts)

            if result is True:
                yes_count += 1
                # 立即回调，边识别边复制
                if on_match_callback:
                    try:
                        on_match_callback(filename, image_path)
                    except Exception as cb_err:
                        logger.error(f"on_match_callback 执行失败 ({filename}): {str(cb_err)}")
            elif result is False:
                no_count += 1
            else:
                error_count += 1

            results.append({
                "filename": filename,
                "path": image_path,
                "result": result,
                "error": None
            })

        except Exception as e:
            error_count += 1
            results.append({
                "filename": filename,
                "path": image_path,
                "result": None,
                "error": str(e)
            })
            logger.error(f"处理 {filename} 时出错: {str(e)}")

        if progress_callback:
            progress_callback(i + 1, total)

    if status_callback:
        status_callback(f"AI 筛选完成！满足: {yes_count} | 不满足: {no_count} | 错误: {error_count}")

    return {
        "results": results,
        "yes_count": yes_count,
        "no_count": no_count,
        "error_count": error_count,
        "_cancelled": False
    }
