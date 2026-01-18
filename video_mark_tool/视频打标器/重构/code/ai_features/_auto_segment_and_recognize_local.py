# This is a method from class VideoTagger
import tkinter as tk
from tkinter import  messagebox, ttk
from PIL import Image
import threading
import io
import base64
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _auto_segment_and_recognize_local(self):
    """使用Ollama API自动按5秒分段并使用AI识别生成标签"""
    
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
    time_info_label = tk.Label(progress_window, text="平均时间: 0s | 剩余时间: 0s", font=self.font)
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
    
    # 在新线程中处理AI识别
    def process_segments():
        try:
            import time
            import numpy as np
            from openai import OpenAI
            
            # 从配置文件读取Ollama API设置
            api_base_url = self.config.get('OLLAMA', 'api_base_url', fallback='http://127.0.0.1:11434/v1')
            api_key = self.config.get('OLLAMA', 'api_key', fallback='ollama')
            model_name = self.config.get('OLLAMA', 'model_name', fallback='qwen3-vl:30b')
            
            # 从配置文件读取采样帧数
            max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
            
            # 从配置文件读取生成参数
            max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=1024)
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
            
            # 存储需要重新处理的片段
            retry_segments = []
            
            # 初始化时间统计
            start_time = time.time()
            completed_count = 0
            
            def extract_frames_from_segment(segment):
                """从视频段落中抽取帧"""
                frames = []
                # 采样最多max_sample_frames帧以提高性能
                total_frames = segment["end"] - segment["start"] + 1
                sample_count = min(max_sample_frames, total_frames)
                
                if total_frames <= sample_count:
                    indices = list(range(segment["start"], segment["end"] + 1))
                else:
                    indices = np.linspace(segment["start"], segment["end"], sample_count, dtype=int)
                
                for idx in indices:
                    if idx < len(self.processed_frames):
                        # 转换为PIL Image
                        frame_rgb = self.processed_frames[idx]
                        pil_frame = Image.fromarray(frame_rgb)
                        frames.append(pil_frame)
                
                # 如果只有一帧，复制以满足视频处理要求
                if len(frames) == 1:
                    frames.append(frames[0])
                    
                return frames
            
            def convert_image_to_base64(image):
                """将PIL图像转换为base64编码"""
                # 调整图片大小
                max_size = (1024, 1024)
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
                
                # 添加所有图片
                for data_url in image_data_urls:
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": data_url}
                    })
                
                messages = [{"role": "user", "content": content_list}]

                # 发送请求并检查生成的提示词长度
                max_attempts = 20  # 最多尝试10次
                for attempt in range(max_attempts):
                    # 发送请求
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_new_tokens,
                        temperature=temperature,
                        top_p=top_p,
                    )
                    
                    caption = response.choices[0].message.content.strip()
                    print(caption)
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
                    
                    # 检查描述长度，如果超过800字则重新生成
                    if len(caption) > 800:
                        logger.info(f"生成的描述长度为 {len(caption)} 字，超过800字限制，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                        # 如果不是最后一次尝试，继续循环重新生成
                        if attempt < max_attempts - 1:
                            continue
                        else:
                            # 最后一次尝试后仍然超长，则截断并添加提示
                            logger.warning(f"经过 {max_attempts} 次尝试后，描述长度仍超过800字，将截断处理")
                            return caption[:800] + "...(内容过长已截断)"
                    
                    # 检查描述是否为空或少于100个字
                    if len(caption) < 100:
                        logger.info(f"生成的描述长度为 {len(caption)} 字，少于100字，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
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
            
            for i, segment in enumerate(segments):
                segment_start_time = time.time()
                
                # 提取片段帧
                frames = extract_frames_from_segment(segment)
                
                # 获取用户自定义的提示词
                user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                
                # 生成描述
                caption = generate_caption_with_ollama(frames, user_prompt)
                
                # 添加到标记列表，不弹窗
                tag_info = {
                    "start": segment["start"],
                    "end": segment["end"],
                    "tag": caption
                }
                self.tags.append(tag_info)
                self.tag_listbox.insert(tk.END, f"帧 {segment['start']}-{segment['end']}: {caption}")
                
                # 更新UI
                self.root.update()
                
                # 更新进度和时间信息
                completed_count = i + 1
                segment_end_time = time.time()
                segment_duration = segment_end_time - segment_start_time
                elapsed_time = segment_end_time - start_time
                avg_time_per_segment = elapsed_time / completed_count
                remaining_segments = len(segments) - completed_count
                estimated_remaining_time = avg_time_per_segment * remaining_segments
                
                # 更新进度（移到处理完成后）
                progress_bar['value'] = completed_count
                progress_info_label.config(text=f"{completed_count}/{len(segments)} 已完成")
                progress_percent.config(text=f"{int((completed_count / len(segments)) * 100)}%")
                time_info_label.config(text=f"平均时间: {avg_time_per_segment:.2f}s | 剩余时间: {estimated_remaining_time:.2f}s")
                progress_window.update()
            
            # 启用导出按钮
            if len(self.tags) > 0:
                self.export_btn.config(state=tk.NORMAL)
                self.save_record_btn.config(state=tk.NORMAL)
            
            # 更新标记可视化
            self.draw_tag_markers()
            
            # 完成后关闭进度窗口并提示
            progress_window.destroy()
            self.root.after(100, lambda: messagebox.showinfo("完成", f"已完成自动分段识别，共生成{len(segments)}个标签"))
            
        except Exception as e:
            progress_window.destroy()
            # 修复变量作用域问题
            error_msg = str(e)
            self.root.after(100, lambda: messagebox.showerror("错误", f"自动分段识别失败: {error_msg}"))
    
    # 启动处理线程
    threading.Thread(target=process_segments, daemon=True).start()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['_auto_segment_and_recognize_local']