import os
import cv2
import json
import base64
import torch
import numpy as np
from openai import OpenAI
from tkinter import filedialog
import tkinter as tk
from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
from PIL import Image
import configparser
import logging
import sys
import subprocess
import math
import shutil
from pathlib import Path
import io
# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BatchVideoProcessor:
    def __init__(self):
        # 创建隐藏的根窗口
        self.root = tk.Tk()
        self.root.withdraw()
        
        # 加载配置
        self.config = configparser.ConfigParser()
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        if os.path.exists(config_path):
            # 修改: 使用 utf-8 编码读取配置文件，避免 UnicodeDecodeError 错误
            self.config.read(config_path, encoding='utf-8')
        else:
            self._create_default_config()
        
        # 初始化模型相关属性
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.model_loaded = False

        # 添加支持的图片格式
        self.supported_image_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')

    def _create_default_config(self):
        """创建默认配置"""
        self.config['PROCESSING'] = {
            'target_frame_rate': '24',
            'target_frame_height': '720',
            'segment_duration': '5',
            'max_sample_frames': '64',
            'max_filename_length': '50'
        }
        
        
        self.config['VLLM'] = {
            'api_base_url': 'http://127.0.0.1:8000/v1',
            'api_key': 'EMPTY',
            'model_name': '/models/Qwen3-VL-8B-Instruct',
            'max_tokens': '1024',
            'temperature': '0.3',
            'top_p': '0.9'
        }
        
        # 添加提示词配置
        self.config['PROMPTS'] = {
            'image_prompt': '以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。'
        }
    
        # 修改: 在创建默认配置文件时也使用 utf-8 编码
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        with open(config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def select_input_folder(self):
        """选择输入文件夹"""
        folder = filedialog.askdirectory(title="选择包含图片文件的文件夹")
        return folder


    def get_image_files(self, folder):
        """获取文件夹中所有图片文件"""
        image_files = []
        for file in os.listdir(folder):
            if file.lower().endswith(self.supported_image_formats):
                image_files.append(os.path.join(folder, file))
        return image_files

    def process_image(self, image_path, common_output_dir=None):##处理单个图片文件
        """处理单个图片文件"""
        logger.info(f"开始处理图片: {image_path}")
        
        # 修改: 如果提供了公共输出目录，则使用它；否则创建专门的文件夹
        if common_output_dir:
            output_dir = common_output_dir
            os.makedirs(output_dir, exist_ok=True)
        else:
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            output_dir = os.path.join(os.path.dirname(image_path), f"{image_name}_processed")#文件夹的名字
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 打开图片
            image = Image.open(image_path).convert('RGB')
            
            # 调整图片大小（如果太大）
            max_size = (1280, 1280)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # AI生成标签
            caption = self.generate_caption_with_ai_for_image(image)
            
            # 保存处理后的图片
            # 修改: 保存在指定的文件夹中，格式改为PNG
            image_basename = os.path.splitext(os.path.basename(image_path))[0]
            output_image_path = os.path.join(output_dir, f"{image_basename}.png")
            image.save(output_image_path, "PNG")
            
            # 保存标签
            txt_output_path = os.path.join(output_dir, f"{image_basename}.txt")
            with open(txt_output_path, 'w', encoding='utf-8') as f:
                f.write(caption)
            
            # 保存元数据（现在无论是否使用公共目录都会创建元数据）
            # 修改: 移除了 if not common_output_dir 条件，使元数据始终被创建
            metadata = {
                "source_image": image_path,
                "processed_image": output_image_path,
                "caption": caption,
                "text_file": txt_output_path
            }
            
            metadata_path = os.path.join(output_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"图片处理完成: {image_path}，生成描述: {caption}")
            
        except Exception as e:
            logger.error(f"处理图片 {image_path} 时出错: {e}")



    def generate_caption_with_ai_for_image(self, image):##使用AI为图片生成描述
        """使用AI为图片生成描述"""
        try:# 尝试使用vLLM API
            api_base_url = self.config.get('VLLM', 'api_base_url', fallback="http://127.0.0.1:8000/v1")
            api_key = self.config.get('VLLM', 'api_key', fallback="EMPTY")
            model_name = self.config.get('VLLM', 'model_name', fallback="/models/Qwen3-VL-8B-Instruct")
            
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            # 转换图片为base64格式
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")  # 修改: 使用PNG格式
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
            data_url = f"data:image/png;base64,{encoded}"  # 修改: 使用PNG格式
            
            # 从配置中获取提示词
            prompt_text = self.config.get('PROMPTS', 'image_prompt', 
                                        fallback='以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。')
            
            # 构造消息
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
            
            # 发送请求
            max_tokens = self.config.getint('VLLM', 'max_tokens', fallback=1024)
            temperature = self.config.getfloat('VLLM', 'temperature', fallback=0.3)
            top_p = self.config.getfloat('VLLM', 'top_p', fallback=0.9)
            
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            
            caption = response.choices[0].message.content.strip()
            return caption
            
        except Exception as e:
            logger.warning(f"使用vLLM API失败: {e}")

    def process_all_images(self, input_folder):
        """处理文件夹中的所有图片"""
        image_files = self.get_image_files(input_folder)
        
        if not image_files:
            logger.info("未找到支持的图片文件")
            return
            
        logger.info(f"找到 {len(image_files)} 个图片文件")
        
        # 修改: 创建一个统一的输出文件夹用于存放所有图片和标签
        common_output_dir = os.path.join(input_folder, "processed_images")
        os.makedirs(common_output_dir, exist_ok=True)
        
        for image_file in image_files:
            try:
                self.process_image(image_file, common_output_dir)
            except Exception as e:
                logger.error(f"处理图片 {image_file} 时出错: {e}")

    def detect_file_types(self, folder):
        """检测文件夹中的文件类型"""
        image_files = []
        
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                if file.lower().endswith(self.supported_image_formats):
                    image_files.append(file_path)
        
        return image_files


    def run(self):
        """运行批处理程序"""
        print("批量视频处理工具")
        print("=" * 30)
        
        # 检查是否通过命令行参数提供了输入文件夹路径
        if len(sys.argv) > 1:
            input_folder = sys.argv[1]
            if not os.path.exists(input_folder):
                print(f"指定的文件夹不存在: {input_folder}")
                return
            print(f"使用命令行参数指定的文件夹: {input_folder}")
        else:
            input_folder = self.select_input_folder()
            if not input_folder:
                print("未选择文件夹，程序退出")
                return
            print(f"选择的文件夹: {input_folder}")
            
        # 检测文件夹中的内容类型并相应处理
        image_files = self.detect_file_types(input_folder)
        
        if image_files:
            print(f"检测到 {len(image_files)} 个图片文件")
            self.process_all_images(input_folder)
        else:
            print("未找到支持的图片文件")
            
        print("所有文件处理完成!")

if __name__ == "__main__":
    processor = BatchVideoProcessor()
    processor.run()