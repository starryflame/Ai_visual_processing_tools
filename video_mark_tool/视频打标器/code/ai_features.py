# AI Features Module - AI 功能模块
# 包含 AI 标签生成、自动分段识别等功能

import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image
import numpy as np
import io
import base64
from openai import OpenAI
import logging
import threading
import time
import cv2

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OllamaAPIClient:
    """Ollama API 客户端封装类，提供统一的 AI 标签生成功能"""
    
    def __init__(self, config):
        """初始化客户端
        
        Args:
            config: configparser.ConfigParser 对象，包含配置信息
        """
        self.config = config
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 OpenAI 客户端"""
        api_base_url = self.config.get('OLLAMA', 'api_base_url', fallback='http://127.0.0.1:11434/v1')
        api_key = self.config.get('OLLAMA', 'api_key', fallback='ollama')
        
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
        model_name = self.config.get('OLLAMA', 'model_name', fallback='qwen3-vl:30b')
        max_new_tokens = self.config.getint('OLLAMA', 'max_new_tokens', fallback=16384)
        temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.3)
        top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
        
        return model_name, max_new_tokens, temperature, top_p
    
    def get_filter_words(self):
        """获取过滤词列表
        
        Returns:
            list: 过滤词列表（小写）
        """
        filter_words = []
        if 'FILTER_WORDS' in self.config:
            filter_words_str = self.config.get('FILTER_WORDS', 'words', fallback='')
            if filter_words_str:
                filter_words = [word.strip().lower() for word in filter_words_str.split(',') if word.strip()]
        return filter_words
    
    def extract_frames(self, processed_frames, start_frame, end_frame):
        """从处理后的帧中提取采样帧
        
        Args:
            processed_frames: 已处理的帧列表（numpy array）
            start_frame: 起始帧索引
            end_frame: 结束帧索引
            
        Returns:
            list: PIL Image 对象列表
        """
        max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
        
        frames = []
        total_frames = end_frame - start_frame + 1
        sample_count = min(max_sample_frames, total_frames)
        
        if total_frames <= sample_count:
            indices = list(range(start_frame, end_frame + 1))
        else:
            indices = np.linspace(start_frame, end_frame, sample_count, dtype=int)
        
        for i in indices:
            if i < len(processed_frames):
                frame_rgb = processed_frames[i]
                pil_frame = Image.fromarray(frame_rgb)
                frames.append(pil_frame)
        
        # 如果只有一帧，复制以满足视频处理要求
        if len(frames) == 1:
            frames.append(frames[0])
        
        return frames
    
    def convert_image_to_base64(self, image):
        """将 PIL 图像转换为 base64 编码
        
        Args:
            image: PIL Image 对象
            
        Returns:
            str: base64 编码的 data URL
        """
        max_size = (720, 720)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{encoded}"
        
        return data_url
    
    def generate_caption_with_ollama(self, frames, prompt_text=None, max_attempts=10, min_length=50):
        """使用 Ollama 为多个帧生成统一描述
        
        Args:
            frames: PIL Image 对象列表
            prompt_text: 用户自定义提示词，默认为 None
            max_attempts: 最大重试次数
            min_length: 最小生成长度
            
        Returns:
            str: 生成的标签文本
        """
        # 转换所有帧为 base64
        image_data_urls = [self.convert_image_to_base64(frame) for frame in frames]
        
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
        
        # 添加所有图片
        for data_url in image_data_urls:
            content_list.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
        
        messages = [{"role": "user", "content": content_list}]
        
        # 获取配置参数
        model_name, max_new_tokens, temperature, top_p = self.get_model_config()
        filter_words = self.get_filter_words()
        
        # 发送请求并检查生成的提示词长度
        for attempt in range(max_attempts):
            try:
                # 发送请求
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=max_new_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )

                caption = response.choices[0].message.content.strip()
                
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
                
                # 检查描述长度是否小于最小值
                if len(caption) < min_length:
                    logger.info(f"生成的描述长度为 {len(caption)} 字，少于 {min_length} 字，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                    # 如果不是最后一次尝试，继续循环重新生成
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        # 最后一次尝试后仍然太短，则返回默认提示
                        logger.warning(f"经过 {max_attempts} 次尝试后，描述长度仍少于 {min_length} 字")
                        return "视频描述内容过短，无法提供有效描述"

                # 如果不包含过滤词且长度符合要求，则返回结果
                if not contains_filter_word:
                    return caption
            
            except Exception as e:
                logger.error(f"API 调用失败 (尝试 {attempt + 1}/{max_attempts}): {str(e)}")
                if attempt < max_attempts - 1:
                    continue
                else:
                    raise
        
        # 如果所有尝试都包含过滤词，则在最后返回时移除过滤词
        logger.warning(f"经过 {max_attempts} 次尝试后，生成的描述仍包含过滤词，将强制移除")
        for word in filter_words:
            caption = caption.replace(word, '')
        return caption.strip() or "视频描述内容已被过滤"


# ==================== 主功能函数 ====================

def auto_segment_and_recognize(self):
    """自动读取视频文件列表并使用 AI 识别生成标签"""
    # 显示选择调用方式的窗口
    method_window = tk.Toplevel(self.root)
    method_window.title("自动读取视频文件列表并使用 AI 识别生成标签")
    method_window.geometry("300x150")
    method_window.transient(self.root)
    method_window.grab_set()
    
    # 居中显示
    method_window.update_idletasks()
    x = (method_window.winfo_screenwidth() // 2) - (300 // 2)
    y = (method_window.winfo_screenheight() // 2) - (150 // 2)
    method_window.geometry(f"300x150+{x}+{y}")

    # 添加进度信息显示标签
    progress_label = tk.Label(method_window, text="准备开始处理...", wraplength=280)
    progress_label.pack(pady=20)

    # 添加取消按钮
    cancel_button = tk.Button(method_window, text="取消", command=lambda: method_window.destroy())
    cancel_button.pack(pady=10)

    def batch_process_videos():
        """批量处理视频文件列表中的所有视频"""
        if not hasattr(self, 'video_list') or not self.video_list:
            messagebox.showwarning("警告", "没有找到视频文件列表")
            method_window.destroy()
            return

        # 记录开始时间
        start_time = time.time()
        processed_count = 0
        total_videos = len(self.video_list)

        for idx, video_path in enumerate(self.video_list):
            try:
                # 更新进度信息
                progress_info = f"正在处理第 {idx + 1}/{total_videos} 个视频：{video_path}"
                # 在 GUI 窗口中更新进度信息
                self.root.after(0, lambda info=progress_info: progress_label.config(text=info))
                print(progress_info)
                
                # 释放之前的视频捕获对象
                if self.cap:
                    self.cap.release()

                # 清空之前处理的帧
                self.processed_frames = []
                self.frames_loaded = False
                self.tags = []  # 清空标记
                self.excluded_segments = []  # 清空排除片段
                self.current_frame_idx = 0

                # 加载当前视频
                self.video_path = video_path
                # 预处理所有帧
                self.preprocess_frames()
                
                self.cap = cv2.VideoCapture(self.video_path)
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.current_frame = 0
                self.start_frame = 0
                self.end_frame = self.total_frames - 1

                #self.add_tag()  # 初始化一个标签范围覆盖整个视频
                # 调用 AI 生成标签（使用本地 Ollama 模型）
                # 调用 AI 生成新标签
                new_caption = self._generate_single_tag_caption()

                if new_caption:  # 如果成功生成了新标签
                    # 创建新的标签信息并添加到标签列表
                    new_tag_info = {
                        "start": self.start_frame,
                        "end": self.end_frame,
                        "tag": new_caption
                    }
                    self.tags = []
                    self.tags.append(new_tag_info)
                    print(f"已添加新标签：{new_caption}")
                    # 更新列表框中的显示
                    self.tag_listbox.delete(0, tk.END)  # 清空列表框
                    self.root.after(0, lambda s=self.start_frame, e=self.end_frame, c=new_caption:
                                   self.tag_listbox.insert(tk.END, f"帧 {s}-{e}: {c}"))

                self.export_tags()  # 导出当前视频的标签
                # 等待 AI 处理完成（这里可以根据实际情况调整等待逻辑）
                time.sleep(1)  # 简单延迟，实际应用中可能需要更复杂的同步机制
                
                processed_count += 1
                print(f"已完成处理：{video_path}")
                
            except Exception as e:
                print(f"处理视频 {video_path} 时出错：{str(e)}")
                continue
        
        # 处理完成后显示统计信息
        elapsed_time = time.time() - start_time
        result_msg = f"批量处理完成!\n共处理 {processed_count}/{total_videos} 个视频\n总耗时：{elapsed_time:.2f} 秒"
        print(result_msg)
        
        # 在主线程中显示完成消息
        self.root.after(0, lambda: messagebox.showinfo("批量处理完成", result_msg))
        # 更新进度标签为完成状态
        self.root.after(0, lambda: progress_label.config(text=result_msg.replace('\n', ' ')))
        
        # 关闭方法选择窗口
        self.root.after(0, lambda: method_window.destroy())

    # 创建选择窗口
    batch_process_videos()


def generate_ai_caption(self):
    """使用 AI 模型生成当前选中视频片段的标签"""
    # 检查是否已设置开始帧和结束帧
    if self.start_frame == 0 and self.end_frame == 0:
        messagebox.showerror("错误", "请先设置开始帧和结束帧")
        return

    # 优先尝试本地模型，失败后再尝试 vLLM API
    try:
        self._generate_ai_caption_local()
    except Exception as local_error:
        print(f"本地模型生成失败：{local_error}")



def _generate_ai_caption_local(self):
    """使用 Ollama API 生成标签"""
    # 启动新线程执行 AI 生成任务
    thread = threading.Thread(target=self._generate_ai_caption_local_thread)
    thread.daemon = True
    thread.start()


def _generate_ai_caption_local_thread(self):
    """在新线程中执行 AI 生成任务"""
    # 显示加载提示
    loading_window = tk.Toplevel(self.root)
    loading_window.title("AI 处理中")
    loading_window.geometry("300x100")
    loading_window.transient(self.root)
    # 移除 grab_set() 调用，让用户可以继续与主窗口交互
    # loading_window.grab_set()
    
    # 将窗口居中显示
    loading_window.update_idletasks()
    x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
    y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
    loading_window.geometry(f"300x100+{x}+{y}")
    
    tk.Label(loading_window, text="正在使用 Ollama 生成标签...", font=self.font).pack(pady=20)
    
    try:
        # 获取选中的视频片段帧
        if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
            # 初始化 Ollama API 客户端
            ollama_client = OllamaAPIClient(self.config)
            
            # 从处理后的帧中提取视频片段
            frames = ollama_client.extract_frames(self.processed_frames, self.start_frame, self.end_frame)
            
            # 获取用户自定义的提示词
            user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
            
            # 生成描述
            caption = ollama_client.generate_caption_with_ollama(frames, user_prompt)
            
            # 在主线程中更新 UI
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
                
                # 在 AI 生成完成后直接打开这个预设标签并允许编辑
                self.show_full_image(thumbnail_frame, caption, new_index)
            
            # 调度 UI 更新到主线程
            self.root.after(0, update_ui)
            
        else:
            # 错误处理也要在主线程中进行
            def show_error():
                messagebox.showerror("错误", "无法获取选中的视频片段")
            self.root.after(0, show_error)
            
    except Exception as e:
        # 错误处理也要在主线程中进行
        def show_error():
            messagebox.showerror("错误", f"AI 标签生成失败：{str(e)}")
        self.root.after(0, show_error)
    finally:
        # 关闭加载窗口也要在主线程中进行
        def close_loading_window():
            loading_window.destroy()
        self.root.after(0, close_loading_window)


def _generate_single_tag_caption(self):
    """为单个标签生成 AI 描述"""
    try:
        # 获取选中的视频片段帧
        if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
            # 初始化 Ollama API 客户端
            ollama_client = OllamaAPIClient(self.config)
            
            # 从处理后的帧中提取视频片段
            frames = ollama_client.extract_frames(self.processed_frames, self.start_frame, self.end_frame)
            
            # 获取用户自定义的提示词
            user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
            
            # 生成描述
            caption = ollama_client.generate_caption_with_ollama(frames, user_prompt)
            
            return caption
        else:
            return None
    except Exception as e:
        print(f"生成单个标签时出错：{str(e)}")
        return None


def _auto_segment_and_recognize_local(self):
    """使用 Ollama API 自动按 5 秒分段并使用 AI 识别生成标签"""
    
    if self.total_frames <= 0 or self.fps <= 0:
        messagebox.showerror("错误", "无效的视频信息")
        return
        
    # 从配置文件读取分段时长
    segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
    frames_per_segment = int(segment_duration * self.fps)
    
    # 创建进度窗口
    progress_window = tk.Toplevel(self.root)
    progress_window.title("自动分段识别中")
    progress_window.geometry("400x200")  # 增加窗口高度以容纳更多信息
    progress_window.transient(self.root)
    #progress_window.grab_set()
    
    # 居中显示
    progress_window.update_idletasks()
    x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
    y = (progress_window.winfo_screenheight() // 2) - (200 // 2)
    progress_window.geometry(f"400x200+{x}+{y}")
    
    tk.Label(progress_window, text="正在自动分段并识别，请稍候...", font=self.font).pack(pady=10)
    
    # 创建进度条
    progress_bar = ttk.Progressbar(progress_window, mode='determinate')
    progress_bar.pack(pady=10, padx=20, fill=tk.X)
    
    # 添加进度信息标签
    progress_info_label = tk.Label(progress_window, text="0/0 已完成", font=self.font)
    progress_info_label.pack()
    
    progress_percent = tk.Label(progress_window, text="0%", font=self.font)
    progress_percent.pack()
    
    # 添加时间信息标签
    time_info_label = tk.Label(progress_window, text="平均时间：0s | 剩余时间：0s", font=self.font)
    time_info_label.pack()
    
    # 计算需要处理的片段数量
    segments = []
    current_frame = 0
    while current_frame < self.total_frames:
        segment_end = min(current_frame + frames_per_segment - 1, self.total_frames - 1)
        
        # 检查这个片段是否在排除列表中
        excluded = False
        for excluded_segment in self.excluded_segments:
            if not (segment_end < excluded_segment["start"] or current_frame > excluded_segment["end"]):
                excluded = True
                break
        
        if not excluded:
            segments.append({
                "start": current_frame,
                "end": segment_end
            })
            
        current_frame += frames_per_segment
    
    progress_bar['maximum'] = len(segments)
    progress_info_label.config(text=f"0/{len(segments)} 已完成")
    
    # 在新线程中处理 AI 识别
    def process_segments():
        try:
            import numpy as np
            
            # 初始化 Ollama API 客户端
            ollama_client = OllamaAPIClient(self.config)
            
            start_time = time.time()
            completed_count = 0
            
            for i, segment in enumerate(segments):
                segment_start_time = time.time()
                
                # 使用封装的方法提取帧
                frames = ollama_client.extract_frames(self.processed_frames, segment["start"], segment["end"])
                
                # 获取用户自定义的提示词
                user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                
                # 生成描述（使用不同的参数）
                caption = ollama_client.generate_caption_with_ollama(
                    frames, 
                    user_prompt,
                    max_attempts=20,
                    min_length=100
                )
                
                tag_info = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "tag": caption
                }
                self.tags.append(tag_info)
                self.tag_listbox.insert(tk.END, f"帧 {segment['start']}-{segment['end']}: {caption}")
                
                self.root.update()
                
                completed_count = i + 1
                segment_end_time = time.time()
                elapsed_time = segment_end_time - start_time
                avg_time_per_segment = elapsed_time / completed_count
                remaining_segments = len(segments) - completed_count
                estimated_remaining_time = avg_time_per_segment * remaining_segments
                
                progress_bar['value'] = completed_count
                progress_info_label.config(text=f"{completed_count}/{len(segments)} 已完成")
                progress_percent.config(text=f"{int((completed_count / len(segments)) * 100)}%")
                time_info_label.config(text=f"平均时间：{avg_time_per_segment:.2f}s | 剩余时间：{estimated_remaining_time:.2f}s")
                progress_window.update()
            
            if len(self.tags) > 0:
                self.export_btn.config(state=tk.NORMAL)
                self.save_record_btn.config(state=tk.NORMAL)
            
            self.draw_tag_markers()
            
            progress_window.destroy()
            self.root.after(100, lambda: messagebox.showinfo("完成", f"已完成自动分段识别，共生成{len(segments)}个标签"))
            
        except Exception as e:
            progress_window.destroy()
            error_msg = str(e)
            self.root.after(100, lambda: messagebox.showerror("错误", f"自动分段识别失败：{error_msg}"))
    
    threading.Thread(target=process_segments, daemon=True).start()


__all__ = [
    'auto_segment_and_recognize',
    'generate_ai_caption',
    '_generate_ai_caption_local',
    '_generate_ai_caption_local_thread',
    '_generate_single_tag_caption',
    '_auto_segment_and_recognize_local',
    'OllamaAPIClient'
]
