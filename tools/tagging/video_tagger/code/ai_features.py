# AI Features Module - AI 功能模块
# 包含 AI 标签生成、自动分段识别等功能

import tkinter as tk
from tkinter import messagebox
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
        max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=16384)
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
        max_size = self.config.getint('PROCESSING', 'image_max_size', fallback=720)
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{encoded}"

        return data_url

    def generate_caption(self, frames, prompt_text=None, max_attempts=10, min_length=50):
        """通过 OpenAI 兼容 API 为多个帧生成统一描述

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

                # 过滤掉模型输出的思考过程 (<think> ... </think>)
                import re
                thought_pattern = r"<think>.*?</think>"
                cleaned_caption = re.sub(thought_pattern, "", caption, flags=re.DOTALL | re.IGNORECASE).strip()
                
                # 如果成功移除了思考标签，则更新 caption
                if cleaned_caption:
                    caption = cleaned_caption
                # 如果没有匹配到标签但包含标签字符（防止部分匹配），也可以尝试简单分割
                elif "</think>" in caption:
                    parts = caption.split("</think>")
                    if len(parts) > 1:
                        caption = parts[-1].strip()

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
    """批量处理视频文件列表，为每个视频生成 AI 标签"""
    # 显示选择调用方式的窗口
    method_window = tk.Toplevel(self.root)
    method_window.title("自动读取视频文件列表并使用 AI 识别生成标签")
    method_window.geometry("450x225")
    method_window.transient(self.root)
    method_window.grab_set()

    # 居中显示
    method_window.update_idletasks()
    x = (method_window.winfo_screenwidth() // 2) - (450 // 2)
    y = (method_window.winfo_screenheight() // 2) - (225 // 2)
    method_window.geometry(f"450x225+{x}+{y}")

    # 安全更新进度标签（窗口销毁后不再更新）
    def safe_update_label(text):
        if progress_label.winfo_exists():
            progress_label.config(text=text)

    # 添加进度信息显示标签
    progress_label = tk.Label(method_window, text="准备开始处理...", wraplength=420, font=("", 10))
    progress_label.pack(pady=15)

    button_frame = tk.Frame(method_window)
    button_frame.pack(pady=10)

    stop_button = tk.Button(button_frame, text="停止后续操作", command=lambda: do_cancel())
    stop_button.pack(side=tk.LEFT, padx=10)

    def do_cancel():
        stop_button.config(text="正在停止...", state=tk.DISABLED)
        progress_label.config(text="正在停止，等待当前视频处理完成...")
        self._cancel_batch = True

    def batch_process_videos():
        """批量处理视频文件列表中的所有视频"""
        if not hasattr(self, 'video_list') or not self.video_list:
            self.root.after(0, lambda: messagebox.showwarning("警告", "没有找到视频文件列表"))
            self.root.after(0, lambda: method_window.destroy())
            return

        # 记录开始时间
        start_time = time.time()
        processed_count = 0
        total_videos = len(self.video_list)

        # 从当前加载的视频位置开始处理（支持中断后接续）
        current_video = getattr(self, 'video_path', '') or ''
        start_idx = 0
        if current_video and current_video in self.video_list:
            start_idx = self.video_list.index(current_video)

        # 初始化 LLM API 客户端
        llm_client = LLMClient(self.config)

        # 初始化取消标志
        self._cancel_batch = False
        cancelled = False

        # 从当前视频位置开始循环（支持跨末尾续接）
        video_paths = self.video_list[start_idx:] + self.video_list[:start_idx]
        for offset, video_path in enumerate(video_paths):
            idx = start_idx + offset
            if idx >= total_videos:
                idx -= total_videos
            # 检查是否已取消
            if getattr(self, '_cancel_batch', False):
                cancelled = True
                result_msg = f"已取消批量处理\n共处理 {processed_count}/{total_videos} 个视频"
                print(result_msg)
                self.root.after(0, lambda m=result_msg: messagebox.showinfo("已取消", m))
                self.root.after(0, method_window.destroy)
                break
            try:
                # 更新进度信息
                progress_info = f"正在处理第 {idx + 1}/{total_videos} 个视频：{video_path}"
                # 在 GUI 窗口中更新进度信息
                self.root.after(0, lambda info=progress_info: safe_update_label(info))
                print(progress_info)
                
                # 释放之前的视频捕获对象
                if hasattr(self, 'cap') and self.cap:
                    self.cap.release()

                # 清空之前处理的帧
                self.processed_frames = []
                self.frames_loaded = False
                self.tags = []  # 清空标记
                self.excluded_segments = []  # 清空排除片段
                self.current_frame_idx = 0

                # 加载当前视频（与双击加载逻辑一致：先打开视频读取属性，再预处理采样）
                self.video_path = video_path
                self.cap = cv2.VideoCapture(self.video_path)
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS)

                # 预处理所有帧（静默模式，按 target_frame_rate 配置采样）
                self.preprocess_frames(silent=True)

                # 刷新主界面显示
                self.current_frame = 0
                self.root.after(0, lambda: self.progress.config(to=self.total_frames-1))
                self.root.after(0, lambda: self.export_fps.set(f"{self.fps:.2f}"))
                self.root.after(0, self.show_frame)
                self.root.after(0, self.draw_tag_markers)

                # 启动视频循环播放（在后台线程中设置标志，主线程的 play_video 会自动循环）
                self.playing = True
                self.root.after(int(1000 / max(self.fps, 1)), self.play_video)

                # 设置起始和结束帧为整个视频 (模拟单个标签覆盖全片的场景)
                self.start_frame = 0
                self.end_frame = self.total_frames - 1

                # 【核心修改】复用 _generate_ai_caption_local_thread 中的 AI 调用逻辑
                # 这里直接调用其内部使用的核心步骤，确保调用方式一致
                try:
                    # 1. 提取帧
                    frames = llm_client.extract_frames(self.processed_frames, self.start_frame, self.end_frame)

                    # 2. 获取用户提示词
                    user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                    
                    # 3. 生成描述 (复用 generate_caption)
                    new_caption = llm_client.generate_caption(frames, user_prompt)

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
                        self.root.after(0, lambda s=self.start_frame, e=self.end_frame, c=new_caption:
                                       self.tag_listbox.delete(0, tk.END) or 
                                       self.tag_listbox.insert(tk.END, f"帧 {s}-{e}: {c}"))

                    self.export_tags(batch_mode=True)  # 导出当前视频的标签（批量模式，无弹窗）

                    # 停止播放，准备处理下一个视频
                    self.playing = False

                except Exception as ai_err:
                    print(f"AI 生成失败 for {video_path}: {str(ai_err)}")
                    # 继续处理下一个视频
                
                # 等待片刻，避免界面卡顿或资源竞争
                time.sleep(0.5)  
                
                processed_count += 1
                print(f"已完成处理：{video_path}")
                
            except Exception as e:
                print(f"处理视频 {video_path} 时出错：{str(e)}")
                continue

        # 处理完成后显示统计信息
        if not cancelled:
            elapsed_time = time.time() - start_time
            result_msg = f"批量处理完成!\n共处理 {processed_count}/{total_videos} 个视频\n总耗时：{elapsed_time:.2f} 秒"
            print(result_msg)

            # 在主线程中显示完成消息
            self.root.after(0, lambda: messagebox.showinfo("批量处理完成", result_msg))
            # 更新进度标签为完成状态
            self.root.after(0, lambda: safe_update_label(result_msg.replace('\n', ' ')))

            # 关闭方法选择窗口
            self.root.after(0, lambda: method_window.destroy())

    # 在新线程中执行批量处理，避免阻塞 UI
    threading.Thread(target=batch_process_videos, daemon=True).start()


def generate_ai_caption(self):
    """使用 AI 模型生成当前选中视频片段的标签"""
    # 检查是否已设置开始帧和结束帧
    if self.start_frame == 0 and self.end_frame == 0:
        messagebox.showerror("错误", "请先设置开始帧和结束帧")
        return

    try:
        self._generate_ai_caption_local()
    except Exception as local_error:
        print(f"AI 生成失败：{local_error}")



def _generate_ai_caption_local(self):
    """通过 OpenAI 兼容 API 生成标签"""
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
    
    tk.Label(loading_window, text="正在使用 AI 生成标签...", font=self.font).pack(pady=20)

    try:
        # 获取选中的视频片段帧
        if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
            # 初始化 LLM API 客户端
            llm_client = LLMClient(self.config)

            # 从处理后的帧中提取视频片段
            frames = llm_client.extract_frames(self.processed_frames, self.start_frame, self.end_frame)

            # 获取用户自定义的提示词
            user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()

            # 生成描述
            caption = llm_client.generate_caption(frames, user_prompt)
            
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
            # 初始化 LLM API 客户端
            llm_client = LLMClient(self.config)

            # 从处理后的帧中提取视频片段
            frames = llm_client.extract_frames(self.processed_frames, self.start_frame, self.end_frame)

            # 获取用户自定义的提示词
            user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()

            # 生成描述
            caption = llm_client.generate_caption(frames, user_prompt)

            return caption
        else:
            return None
    except Exception as e:
        print(f"生成单个标签时出错：{str(e)}")
        return None


__all__ = [
    'auto_segment_and_recognize',
    'generate_ai_caption',
    '_generate_ai_caption_local',
    '_generate_ai_caption_local_thread',
    '_generate_single_tag_caption',
    'LLMClient'
]
