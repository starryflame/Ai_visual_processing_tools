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
        
        # 支持的视频格式
        self.supported_formats = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
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
        
        self.config['MODEL'] = {
            'qwen_vl_model_path': r'J:\models\LLM\Qwen-VL\Qwen3-VL-8B-Instruct',
            'torch_dtype': 'fp32',
            'max_new_tokens': '1024',
            'temperature': '0.6',
            'top_p': '0.9'
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
            'video_prompt': '以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。',
            'image_prompt': '以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。'
        }
    
        # 修改: 在创建默认配置文件时也使用 utf-8 编码
        config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        with open(config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)

    def select_input_folder(self):
        """选择输入文件夹"""
        folder = filedialog.askdirectory(title="选择包含视频文件的文件夹")
        return folder

    def get_video_files(self, folder):
        """获取文件夹中所有视频文件"""
        video_files = []
        for file in os.listdir(folder):
            if file.lower().endswith(self.supported_formats):
                video_files.append(os.path.join(folder, file))
        return video_files

    def get_image_files(self, folder):
        """获取文件夹中所有图片文件"""
        image_files = []
        for file in os.listdir(folder):
            if file.lower().endswith(self.supported_image_formats):
                image_files.append(os.path.join(folder, file))
        return image_files

    def resize_to_720p(self, frame):
        """将帧调整为720p分辨率"""
        target_height = self.config.getint('PROCESSING', 'target_frame_height', fallback=720)
        h, w = frame.shape[:2]
        
        if h <= target_height:
            return frame
            
        new_height = target_height
        new_width = int(w * (new_height / h))
        resized_frame = cv2.resize(frame, (new_width, new_height))
        return resized_frame

    def process_video(self, video_path):##处理单个视频文件
        """处理单个视频文件"""
        logger.info(f"开始处理视频: {video_path}")
        
        # 创建输出文件夹
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.join(os.path.dirname(video_path), f"{video_name}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            return
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        if total_frames <= 0 or fps <= 0:
            logger.error(f"无效的视频信息: {video_path}")
            cap.release()
            return
            
        logger.info(f"视频信息 - 总帧数: {total_frames}, FPS: {fps}")
        
        # 从配置读取目标帧率
        target_fps = self.config.getint('PROCESSING', 'target_frame_rate', fallback=24)
        if fps > target_fps:
            frame_interval = fps / target_fps
            effective_fps = target_fps
        else:
            frame_interval = 1
            effective_fps = fps
            
        # 处理所有帧
        processed_frames = []
        i = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if i % frame_interval < 1:
                # 转换颜色格式
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 调整为720p
                frame = self.resize_to_720p(frame)
                processed_frames.append(frame)
                
            i += 1
            
        cap.release()
        
        # 计算分段参数
        segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
        frames_per_segment = int(segment_duration * effective_fps)
        
        # 分段处理
        segments = []
        current_frame = 0
        segment_index = 0
        
        while current_frame < len(processed_frames):
            segment_end = min(current_frame + frames_per_segment - 1, len(processed_frames) - 1)
            
            # 提取片段帧
            segment_frames = processed_frames[current_frame:segment_end+1]
            
            # 抽帧以提高性能
            max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
            if len(segment_frames) > max_sample_frames:
                indices = np.linspace(0, len(segment_frames)-1, max_sample_frames, dtype=int)
                sampled_frames = [segment_frames[i] for i in indices]
            else:
                sampled_frames = segment_frames
                
            # 如果只有一帧，复制以满足视频处理要求
            if len(sampled_frames) == 1:
                sampled_frames.append(sampled_frames[0])
            
            # AI生成标签
            caption = self.generate_caption_with_ai(sampled_frames)
            
            # 保存片段视频
            if segment_frames:
                first_frame = segment_frames[0]
                height, width = first_frame.shape[:2]
                
                # 生成安全的文件名
                safe_caption = "".join(c for c in caption if c.isalnum() or c in (' ', '-', '_')).rstrip()
                max_filename_length = self.config.getint('PROCESSING', 'max_filename_length', fallback=50)
                safe_caption = safe_caption[:max_filename_length] if len(safe_caption) > max_filename_length else safe_caption
                safe_caption = safe_caption.replace(" ", "_") if safe_caption else f"segment_{segment_index+1:03d}"
                
                # 生成文件名
                filename = f"{segment_index+1:03d}_{safe_caption}"
                video_output_path = os.path.join(output_dir, f"{filename}.mp4")
                txt_output_path = os.path.join(output_dir, f"{filename}.txt")
                
                # 写入视频
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(video_output_path, fourcc, effective_fps, (width, height))
                
                for frame in segment_frames:
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    out.write(frame_bgr)
                out.release()
                
                # 写入标签
                with open(txt_output_path, 'w', encoding='utf-8') as f:
                    f.write(caption)
                
                segments.append({
                    "index": segment_index,
                    "start_frame": current_frame,
                    "end_frame": segment_end,
                    "caption": caption,
                    "video_path": video_output_path,
                    "text_path": txt_output_path
                })
                
                logger.info(f"已保存片段 {segment_index+1}: {caption}")
            
            current_frame += frames_per_segment
            segment_index += 1
            
        # 保存元数据
        metadata = {
            "source_video": video_path,
            "source_fps": float(fps),
            "processed_fps": float(effective_fps),
            "total_frames": len(processed_frames),
            "segments": segments
        }
        
        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        logger.info(f"视频处理完成: {video_path}，共生成 {len(segments)} 个片段")

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
            max_size = (1024, 1024)
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

    def generate_caption_with_ai(self, frames):##使用AI生成视频片段描述
        """使用AI生成视频片段描述"""
        try:# 尝试使用vLLM API
            # 尝试使用vLLM API
            api_base_url = self.config.get('VLLM', 'api_base_url', fallback="http://127.0.0.1:8000/v1")
            api_key = self.config.get('VLLM', 'api_key', fallback="EMPTY")
            model_name = self.config.get('VLLM', 'model_name', fallback="/models/Qwen3-VL-8B-Instruct")
            
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            # 转换帧为base64格式
            frame_data_urls = []
            # 修改: 使用配置中的max_sample_frames值来控制抽取帧数，而不是固定的14帧
            max_sample_frames_for_ai = self.config.getint('PROCESSING', 'max_sample_frames', fallback=21)
            sample_interval = max(1, len(frames) // max_sample_frames_for_ai)
            for frame in frames[::sample_interval]:  # 使用配置的抽帧数
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                _, buffer = cv2.imencode(".png", frame_bgr)  # 修改: 使用PNG格式
                encoded = base64.b64encode(buffer).decode("utf-8")
                data_url = f"data:image/png;base64,{encoded}"  # 修改: 使用PNG格式
                frame_data_urls.append(data_url)
            
            # 从配置中获取提示词
            prompt_text = self.config.get('PROMPTS', 'video_prompt', 
                                        fallback='以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。')
            
            # 构造消息
            content_list = [
                {
                    "type": "text",
                    "text": prompt_text
                }
            ]
            
            for url in frame_data_urls:
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })
            
            messages = [{"role": "user", "content": content_list}]
            
            # 发送请求
            max_tokens = self.config.getint('VLLM', 'max_tokens', fallback=1024)
            temperature = self.config.getfloat('VLLM', 'temperature', fallback=0.3)
            top_p = self.config.getfloat('VLLM', 'top_p', fallback=0.9)
            
            # 添加重试逻辑，如果生成的描述超过1000字则重新生成
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                
                caption = response.choices[0].message.content.strip()
                
                # 检查生成的描述是否超过1000字
                if len(caption) <= 1000:
                    return caption
                else:
                    logger.info(f"生成的描述超过1000字（当前长度：{len(caption)}），正在重新生成...（第{retry_count+1}次重试）")
                    retry_count += 1
                    # 调整参数以尝试获得更短的输出
                    temperature = min(1.0, temperature + 0.1)  # 增加随机性
                    max_tokens = max(256, max_tokens - 128)    # 减少最大token数
            
            logger.warning(f"已达最大重试次数，返回最后生成的结果（长度：{len(caption)}）")
            return caption
            
        except Exception as e:# 使用本地模型
            logger.warning(f"使用vLLM API失败: {e}，尝试使用本地模型")
            
            # 使用本地模型
            if not self.model_loaded:
                self.load_local_model()
                
            if not self.model_loaded:
                return "无法生成描述"
                
            try:
                # 修改: 使用配置中的max_sample_frames值来控制抽取帧数，而不是固定的14帧
                max_sample_frames_for_ai = self.config.getint('PROCESSING', 'max_sample_frames', fallback=21)
                sample_interval = max(1, len(frames) // max_sample_frames_for_ai)
                pil_frames = [Image.fromarray(frame) for frame in frames[::sample_interval]]
                
                if len(pil_frames) == 1:
                    pil_frames.append(pil_frames[0])
                
                # 从配置中获取提示词
                prompt_text = self.config.get('PROMPTS', 'video_prompt', 
                                            fallback='以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。')
                
                conversation = [{
                    "role": "user",
                    "content": [
                        {"type": "video", "video": pil_frames},
                        {"type": "text", "text": prompt_text}
                    ]
                }]
                
                text_prompt = self.processor.apply_chat_template(
                    conversation,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                inputs = self.processor(
                    text=text_prompt,
                    videos=[pil_frames],
                    return_tensors="pt"
                )
                
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
                
                max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=1024)
                temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.6)
                top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
                
                # 添加重试逻辑，如果生成的描述超过1000字则重新生成
                retry_count = 0
                max_retries = 3
                while retry_count < max_retries:
                    with torch.no_grad():
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=max_new_tokens,
                            do_sample=True,
                            temperature=temperature,
                            top_p=top_p
                        )
                    
                    input_ids_len = inputs["input_ids"].shape[1]
                    caption = self.tokenizer.decode(
                        outputs[0, input_ids_len:],
                        skip_special_tokens=True
                    )
                    caption = caption.strip()
                    
                    # 检查生成的描述是否超过1000字
                    if len(caption) <= 1000:
                        return caption
                    else:
                        logger.info(f"生成的描述超过1000字（当前长度：{len(caption)}），正在重新生成...（第{retry_count+1}次重试）")
                        retry_count += 1
                        # 调整参数以尝试获得更短的输出
                        temperature = min(1.0, temperature + 0.1)  # 增加随机性
                        max_new_tokens = max(256, max_new_tokens - 128)  # 减少最大token数
                
                logger.warning(f"已达最大重试次数，返回最后生成的结果（长度：{len(caption)}）")
                return caption
                
            except Exception as local_e:
                logger.error(f"本地模型生成失败: {local_e}")
                return "无法生成描述"

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
            
        except Exception as e:# 使用本地模型
            logger.warning(f"使用vLLM API失败: {e}，尝试使用本地模型")
            
            if not self.model_loaded:
                self.load_local_model()
                
            if not self.model_loaded:
                return "无法生成描述"
                
            try:
                # 从配置中获取提示词
                prompt_text = self.config.get('PROMPTS', 'image_prompt', 
                                            fallback='以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。')
                
                conversation = [{
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": prompt_text}
                    ]
                }]
                
                text_prompt = self.processor.apply_chat_template(
                    conversation,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                inputs = self.processor(
                    text=text_prompt,
                    images=[image],
                    return_tensors="pt"
                )
                
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
                
                max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=1024)
                temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.6)
                top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
                
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=True,
                        temperature=temperature,
                        top_p=top_p
                    )
                
                input_ids_len = inputs["input_ids"].shape[1]
                caption = self.tokenizer.decode(
                    outputs[0, input_ids_len:],
                    skip_special_tokens=True
                )
                caption = caption.strip()
                
                return caption
                
            except Exception as local_e:
                logger.error(f"本地模型生成失败: {local_e}")
                return "无法生成描述"

    def load_local_model(self):##加载本地模型
        """加载本地模型"""
        try:
            model_path = self.config.get('MODEL', 'qwen_vl_model_path', fallback=r"J:\models\LLM\Qwen-VL\Qwen3-VL-4B-Instruct")
            
            if not os.path.exists(model_path):
                logger.error(f"模型路径不存在: {model_path}")
                return
                
            torch_dtype_str = self.config.get('MODEL', 'torch_dtype', fallback='fp32')
            if torch_dtype_str == 'fp16':
                torch_dtype = torch.float16
            elif torch_dtype_str == 'bf16':
                torch_dtype = torch.bfloat16
            else:
                torch_dtype = torch.float32
                
            self.model = AutoModelForVision2Seq.from_pretrained(
                model_path,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch_dtype
            ).eval()
            
            self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            self.model_loaded = True
            
            logger.info("本地模型加载成功")
            
        except Exception as e:
            logger.error(f"本地模型加载失败: {e}")

    def get_video_duration(self, video_path):
        """获取视频时长"""
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"无法获取视频时长: {e}")
            return 0

    def split_video_intelligently(self, input_path, output_dir, filename):
        """智能分割视频，尽量对半分且避免过小片段"""
        duration = self.get_video_duration(input_path)
        if duration <= 60:  # 1分钟=60秒
            print(f"{filename} 时长不足1分钟，无需分割")
            return []
        
        # 计算分割策略：尽量对半分，但确保每段不超过1分钟
        num_segments = max(2, math.ceil(duration / 60))  # 至少分成2段，每段不超过1分钟
        segment_duration = duration / num_segments
        
        # 如果分割后每段都小于30秒，则不进行分割
        if segment_duration < 30:
            print(f"{filename} 分割后片段太小，跳过分割")
            return []
        
        print(f"将 {filename} 分割为 {num_segments} 个片段，每段约{segment_duration/60:.1f}分钟")
        
        # 创建输出目录
        base_name = Path(filename).stem
        suffix = Path(filename).suffix
        
        split_files = []
        
        # 分割前n-1个片段
        for i in range(num_segments - 1):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            
            output_file = os.path.join(output_dir, f"{base_name}_part{i+1:02d}{suffix}")
            cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_time), '-to', str(end_time),
                '-c', 'copy', output_file
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            split_files.append(output_file)
            print(f"已生成: {os.path.basename(output_file)} ({end_time-start_time:.1f}秒)")
        
        # 处理最后一个片段
        start_time = (num_segments - 1) * segment_duration
        output_file = os.path.join(output_dir, f"{base_name}_part{num_segments:02d}{suffix}")
        cmd = [
            'ffmpeg', '-i', input_path,
            '-ss', str(start_time),
            '-c', 'copy', output_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        split_files.append(output_file)
        print(f"已生成: {os.path.basename(output_file)} ({duration-start_time:.1f}秒)")
        
        return split_files

    def process_folder_for_splitting(self, input_folder):
        """处理指定文件夹中的所有视频文件并分割过长视频"""
        # 支持的视频格式
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp'}
        
        # 创建输出目录
        output_dir = os.path.join(input_folder, "split_videos")
        os.makedirs(output_dir, exist_ok=True)
        
        split_files = []
        
        # 遍历文件夹中的所有文件
        for filename in os.listdir(input_folder):
            file_path = os.path.join(input_folder, filename)
            
            # 检查是否为文件且为视频格式
            if os.path.isfile(file_path) and Path(filename).suffix.lower() in video_extensions:
                print(f"正在处理: {filename}")
                duration = self.get_video_duration(file_path)
                
                # 如果视频小于等于1分钟，直接复制到输出目录
                if duration <= 60:
                    output_file = os.path.join(output_dir, filename)
                    shutil.copy2(file_path, output_file)
                    split_files.append(output_file)
                    print(f"已复制: {filename} (无需分割)")
                else:
                    # 否则进行分割
                    files = self.split_video_intelligently(file_path, output_dir, filename)
                    split_files.extend(files)
        
        print(f"所有视频分割完成，分割文件保存在: {output_dir}")
        return output_dir, split_files

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
        video_files = []
        image_files = []
        
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                if file.lower().endswith(self.supported_formats):
                    video_files.append(file_path)
                elif file.lower().endswith(self.supported_image_formats):
                    image_files.append(file_path)
        
        return video_files, image_files

    def process_all_videos(self, input_folder):
        """处理文件夹中的所有视频"""
        # 先进行视频分割
        split_dir, split_files = self.process_folder_for_splitting(input_folder)
        
        # 如果有分割后的文件，则处理这些文件；否则处理原始文件
        if split_files:
            video_files = split_files
            processing_folder = split_dir
        else:
            video_files = self.get_video_files(input_folder)
            processing_folder = input_folder
        
        if not video_files:
            logger.info("未找到支持的视频文件")
            return
            
        logger.info(f"找到 {len(video_files)} 个视频文件")
        
        for video_file in video_files:
            try:
                self.process_video(video_file)
            except Exception as e:
                logger.error(f"处理视频 {video_file} 时出错: {e}")

    def process_mixed_content(self, input_folder):
        """处理混合内容（视频和图片）"""
        video_files, image_files = self.detect_file_types(input_folder)
        
        if video_files:
            logger.info(f"检测到 {len(video_files)} 个视频文件，开始处理...")
            # 处理视频文件
            # 先进行视频分割
            split_dir, split_files = self.process_folder_for_splitting(input_folder)
            
            # 如果有分割后的文件，则处理这些文件；否则处理原始文件
            if split_files:
                files_to_process = split_files
                processing_folder = split_dir
            else:
                files_to_process = video_files
                processing_folder = input_folder
            
            for video_file in files_to_process:
                try:
                    self.process_video(video_file)
                except Exception as e:
                    logger.error(f"处理视频 {video_file} 时出错: {e}")
        
        if image_files:
            logger.info(f"检测到 {len(image_files)} 个图片文件，开始处理...")
            # 修改: 为所有图片创建一个共同的输出目录
            common_output_dir = os.path.join(input_folder, "processed_images")
            os.makedirs(common_output_dir, exist_ok=True)
            
            # 处理图片文件
            for image_file in image_files:
                try:
                    self.process_image(image_file, common_output_dir)
                except Exception as e:
                    logger.error(f"处理图片 {image_file} 时出错: {e}")

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
        video_files, image_files = self.detect_file_types(input_folder)
        
        if video_files and image_files:
            print(f"检测到 {len(video_files)} 个视频文件和 {len(image_files)} 个图片文件")
            self.process_mixed_content(input_folder)
        elif video_files:
            print(f"检测到 {len(video_files)} 个视频文件")
            self.process_all_videos(input_folder)
        elif image_files:
            print(f"检测到 {len(image_files)} 个图片文件")
            self.process_all_images(input_folder)
        else:
            print("未找到支持的视频或图片文件")
            
        print("所有文件处理完成!")

if __name__ == "__main__":
    processor = BatchVideoProcessor()
    processor.run()