import base64
import io
import torch
import cv2
import numpy as np
from openai import OpenAI
from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
from PIL import Image
import logging
import os
logger = logging.getLogger(__name__)

class AIProcessor:
    def __init__(self, config_manager):
        self.config = config_manager
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.model_loaded = False
    
    def load_local_model(self):#加载本地模型
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
            
            print("本地模型加载成功")
            
        except Exception as e:
            logger.error(f"本地模型加载失败: {e}")

    def generate_video_caption_with_ai(self, frames):#使用AI生成视频片段描述
        """使用AI生成视频片段描述"""
        try:
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
            max_sample_frames_for_ai = self.config.getint('PROCESSING', 'max_sample_frames', fallback=21)
            sample_interval = max(1, len(frames) // max_sample_frames_for_ai)
            for frame in frames[::sample_interval]:  # 使用配置的抽帧数
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                _, buffer = cv2.imencode(".png", frame_bgr)  # 使用PNG格式
                encoded = base64.b64encode(buffer).decode("utf-8")
                data_url = f"data:image/png;base64,{encoded}"  # 使用PNG格式
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
            
            # 获取过滤词列表
            filter_keywords_str = self.config.get('FILTER', 'keywords', fallback='无关,无法,抱歉,对不起,不知道,不清楚,不相关,重复,无意义,胡言乱语,乱码,废话')
            filter_keywords = [kw.strip() for kw in filter_keywords_str.split(',') if kw.strip()]
            
            # 从配置中获取最大字符数限制
            max_caption_length = self.config.getint('PROCESSING', 'max_caption_length', fallback=1000)
            
            # 添加重试逻辑，如果生成的描述超过指定字数或包含过滤词则重新生成
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
                
                # 检查生成的描述是否超过指定字数或包含过滤词
                contains_filter_word = any(keyword in caption for keyword in filter_keywords)
                if len(caption) <= max_caption_length and not contains_filter_word:
                    return caption
                else:
                    if len(caption) > max_caption_length:
                        print(f"生成的描述超过{max_caption_length}字（当前长度：{len(caption)}），正在重新生成...（第{retry_count+1}次重试）")
                    if contains_filter_word:
                        found_keywords = [kw for kw in filter_keywords if kw in caption]
                        print(f"生成的描述包含过滤词 {found_keywords}，正在重新生成...（第{retry_count+1}次重试）")
                    retry_count += 1
                    # 调整参数以尝试获得更好的输出
                    temperature = min(1.0, temperature + 0.1)  # 增加随机性
                    max_tokens = max(256, max_tokens - 128)    # 减少最大token数
            
            logger.warning(f"已达最大重试次数，返回最后生成的结果（长度：{len(caption)}）")
            return caption
            
        except Exception as e:
            logger.warning(f"使用vLLM API失败: {e}，尝试使用本地模型")
            
            # 使用本地模型
            if not self.model_loaded:
                self.load_local_model()
                
            if not self.model_loaded:
                return "无法生成描述"
                
            try:
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
                
                # 获取过滤词列表
                filter_keywords_str = self.config.get('FILTER', 'keywords', fallback='无关,无法,抱歉,对不起,不知道,不清楚,不相关,重复,无意义,胡言乱语,乱码,废话')
                filter_keywords = [kw.strip() for kw in filter_keywords_str.split(',') if kw.strip()]
                
                # 从配置中获取最大字符数限制
                max_caption_length = self.config.getint('PROCESSING', 'max_caption_length', fallback=1000)
                
                # 添加重试逻辑，如果生成的描述超过指定字数或包含过滤词则重新生成
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
                    
                    # 检查生成的描述是否超过指定字数或包含过滤词
                    contains_filter_word = any(keyword in caption for keyword in filter_keywords)
                    if len(caption) <= max_caption_length and not contains_filter_word:
                        return caption
                    else:
                        if len(caption) > max_caption_length:
                            print(f"生成的描述超过{max_caption_length}字（当前长度：{len(caption)}），正在重新生成...（第{retry_count+1}次重试）")
                        if contains_filter_word:
                            found_keywords = [kw for kw in filter_keywords if kw in caption]
                            print(f"生成的描述包含过滤词 {found_keywords}，正在重新生成...（第{retry_count+1}次重试）")
                        retry_count += 1
                        # 调整参数以尝试获得更好的输出
                        temperature = min(1.0, temperature + 0.1)  # 增加随机性
                        max_new_tokens = max(256, max_new_tokens - 128)  # 减少最大token数
                
                logger.warning(f"已达最大重试次数，返回最后生成的结果（长度：{len(caption)}）")
                return caption
                
            except Exception as local_e:
                logger.error(f"本地模型生成失败: {local_e}")
                return "无法生成描述"

    def generate_image_caption_with_ai(self, image):#使用AI为图片生成描述
        """使用AI为图片生成描述"""
        try:
            # 尝试使用vLLM API
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
            image.save(buffered, format="PNG")  # 使用PNG格式
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
            data_url = f"data:image/png;base64,{encoded}"  # 使用PNG格式
            
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
            
            # 从配置中获取最大字符数限制
            max_caption_length = self.config.getint('PROCESSING', 'max_caption_length', fallback=1000)
            
            # 添加重试逻辑，如果生成的描述超过指定字数则重新生成
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
                
                # 检查生成的描述是否超过指定字数
                if len(caption) <= max_caption_length:
                    return caption
                else:
                    print(f"生成的描述超过{max_caption_length}字（当前长度：{len(caption)}），正在重新生成...（第{retry_count+1}次重试）")
                    retry_count += 1
                    # 调整参数以尝试获得更短的输出
                    temperature = min(1.0, temperature + 0.1)  # 增加随机性
                    max_tokens = max(256, max_tokens - 128)    # 减少最大token数
            
            logger.warning(f"已达最大重试次数，返回最后生成的结果（长度：{len(caption)}）")
            return caption
            
        except Exception as e:
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
                
                # 从配置中获取最大字符数限制
                max_caption_length = self.config.getint('PROCESSING', 'max_caption_length', fallback=1000)
                
                # 添加重试逻辑，如果生成的描述超过指定字数则重新生成
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
                    
                    # 检查生成的描述是否超过指定字数
                    if len(caption) <= max_caption_length:
                        return caption
                    else:
                        print(f"生成的描述超过{max_caption_length}字（当前长度：{len(caption)}），正在重新生成...（第{retry_count+1}次重试）")
                        retry_count += 1
                        # 调整参数以尝试获得更短的输出
                        temperature = min(1.0, temperature + 0.1)  # 增加随机性
                        max_new_tokens = max(256, max_new_tokens - 128)  # 减少最大token数
                
                logger.warning(f"已达最大重试次数，返回最后生成的结果（长度：{len(caption)}）")
                return caption
                
            except Exception as local_e:
                logger.error(f"本地模型生成失败: {local_e}")
                return "无法生成描述"