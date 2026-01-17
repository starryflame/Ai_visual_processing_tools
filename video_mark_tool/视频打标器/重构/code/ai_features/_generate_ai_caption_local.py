import tkinter as tk
from tkinter import messagebox
from PIL import Image
import numpy as np
import io
import base64
from openai import OpenAI
import logging
import re
import threading  # 添加线程支持
# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _generate_ai_caption_local(self):
    """使用Ollama API生成标签"""
    # 启动新线程执行AI生成任务
    thread = threading.Thread(target=self._generate_ai_caption_local_thread)
    thread.daemon = True
    thread.start()


def _generate_ai_caption_local_thread(self):
    """在新线程中执行AI生成任务"""
    # 显示加载提示
    loading_window = tk.Toplevel(self.root)
    loading_window.title("AI处理中")
    loading_window.geometry("300x100")
    loading_window.transient(self.root)
    # 移除 grab_set() 调用，让用户可以继续与主窗口交互
    # loading_window.grab_set()
    
    # 将窗口居中显示
    loading_window.update_idletasks()
    x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
    y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
    loading_window.geometry(f"300x100+{x}+{y}")
    
    tk.Label(loading_window, text="正在使用Ollama生成标签...", font=self.font).pack(pady=20)
    
    try:
        # 获取选中的视频片段帧
        if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
            # 从处理后的帧中提取视频片段
            frames = []
            # 从配置文件读取采样帧数
            max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
            #print(f"采样帧数: {max_sample_frames}")
            # 采样最多max_sample_frames帧以提高性能
            total_frames = self.end_frame - self.start_frame + 1
            sample_count = min(max_sample_frames, total_frames)
            
            if total_frames <= sample_count:
                indices = list(range(self.start_frame, self.end_frame + 1))
            else:
                indices = np.linspace(self.start_frame, self.end_frame, sample_count, dtype=int)
            
            for i in indices:
                if i < len(self.processed_frames):
                    # 转换为PIL Image
                    frame_rgb = self.processed_frames[i]
                    pil_frame = Image.fromarray(frame_rgb)
                    frames.append(pil_frame)
            
            # 如果只有一帧，复制以满足视频处理要求
            if len(frames) == 1:
                frames.append(frames[0])
            
            # 从配置文件读取Ollama API设置
            api_base_url = self.config.get('OLLAMA', 'api_base_url', fallback='http://127.0.0.1:11434/v1')
            api_key = self.config.get('OLLAMA', 'api_key', fallback='ollama')
            model_name = self.config.get('OLLAMA', 'model_name', fallback='qwen3-vl:30b')
            
            # 从配置文件读取生成参数
            max_new_tokens = self.config.getint('OLLAMA', 'max_new_tokens', fallback=16384)
            #print(f"最大生成长度: {max_new_tokens}")
            temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.3)
            top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
            
            # 读取过滤词列表
            filter_words = []
            if 'FILTER_WORDS' in self.config:
                filter_words_str = self.config.get('FILTER_WORDS', 'words', fallback='')
                if filter_words_str:
                    filter_words = [word.strip().lower() for word in filter_words_str.split(',') if word.strip()]
            
            # 初始化客户端
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            def convert_image_to_base64(image):
                """将PIL图像转换为base64编码"""
                # 调整图片大小
                max_size = (720, 720)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 转换图片为base64格式
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
                data_url = f"data:image/png;base64,{encoded}"
                
                return data_url
            
            def generate_caption_with_ollama(frames, prompt_text=None):
                """使用Ollama为多个帧生成统一描述"""
                # 转换所有帧为base64
                image_data_urls = [convert_image_to_base64(frame) for frame in frames]
                # 使用传入的提示词或者默认提示词
                if prompt_text is None or prompt_text.strip() == "":
                    prompt_text = '你是一名专业的图片内容描述大师，请放心使用最大胆直白的语言和明确清晰的句子描述，禁止隐瞒，暗示或者用笼统和词义不单一的词汇。详细全面描述画面里的所有元素。只输出内容本身，不要重复和输出其他内容，中文回答。'
                
                # 构造消息内容
                content_list = [
                    {
                        "type": "text",
                        "text": prompt_text
                    }
                ]
                print(f"提示词: {prompt_text}")
                # 添加所有图片
                for data_url in image_data_urls:
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": data_url}
                    })
                
                messages = [{"role": "user", "content": content_list}]

                # 发送请求并检查生成的提示词长度
                max_attempts = 10  # 最多尝试10次
                for attempt in range(max_attempts):
                    # 发送请求
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_new_tokens,
                        temperature=temperature,
                        top_p=top_p,
                    )
                    print(f"生成描述: {response}")

                    caption = response.choices[0].message.content.strip()
                    #print(caption)
                    # 检查是否包含过滤词
                    contains_filter_word = False
                    caption_lower = caption.lower()
                    for word in filter_words:
                        if word in caption_lower:
                            contains_filter_word = True
                            logger.info(f"生成的描述包含过滤词 '{word}'，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                            break
                    
                    # 如果包含过滤词且不是最后一次尝试，则重新生成
                    if contains_filter_word and attempt < max_attempts - 1:
                        continue
                    
                    # 检查描述是否为空或少于50个字
                    if len(caption) < 50:
                        logger.info(f"生成的描述长度为 {len(caption)} 字，少于50字，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                        # 如果不是最后一次尝试，继续循环重新生成
                        if attempt < max_attempts - 1:
                            continue
                        else:
                            # 最后一次尝试后仍然太短，则返回默认提示
                            logger.warning(f"经过 {max_attempts} 次尝试后，描述长度仍少于100字")
                            return "视频描述内容过短，无法提供有效描述"
                        

                    # 如果不包含过滤词且长度符合要求，则返回结果
                    if not contains_filter_word:
                        return caption
                
                # 如果所有尝试都包含过滤词，则在最后返回时移除过滤词
                logger.warning(f"经过 {max_attempts} 次尝试后，生成的描述仍包含过滤词，将强制移除")
                for word in filter_words:
                    caption = caption.replace(word, '')
                return caption.strip() or "视频描述内容已被过滤"
            
            # 获取用户自定义的提示词
            user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
            
            # 生成描述
            caption = generate_caption_with_ollama(frames, user_prompt)
            
            # 在主线程中更新UI
            def update_ui():
                # 添加到预设列表
                # 使用第一帧作为缩略图
                print(self.start_frame,self.end_frame)

                thumbnail_frame = self.processed_frames[self.start_frame].copy()
                new_index = len(self.caption_presets)
                self.caption_presets.append({
                    "caption": caption,
                    "image": thumbnail_frame
                })
                
                # 创建新的预设项显示
                self.create_preset_item(new_index, caption, thumbnail_frame)
                
                # 在AI生成完成后直接打开这个预设标签并允许编辑
                self.show_full_image(thumbnail_frame, caption, new_index)
            
            # 调度UI更新到主线程
            self.root.after(0, update_ui)
            
        else:
            # 错误处理也要在主线程中进行
            def show_error():
                messagebox.showerror("错误", "无法获取选中的视频片段")
            self.root.after(0, show_error)
            
    except Exception as e:
        # 错误处理也要在主线程中进行
        def show_error():
            messagebox.showerror("错误", f"AI标签生成失败: {str(e)}")
        self.root.after(0, show_error)
    finally:
        # 关闭加载窗口也要在主线程中进行
        def close_loading_window():
            loading_window.destroy()
        self.root.after(0, close_loading_window)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['_generate_ai_caption_local', '_generate_ai_caption_local_thread']