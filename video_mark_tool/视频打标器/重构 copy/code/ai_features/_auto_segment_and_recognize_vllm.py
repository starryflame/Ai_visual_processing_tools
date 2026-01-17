# This is a method from class VideoTagger
import cv2
import tkinter as tk
from tkinter import messagebox, ttk
import threading
import numpy as np
import base64
import time


def _auto_segment_and_recognize_vllm(self):
    """使用vLLM API自动按5秒分段并使用AI识别生成标签"""
    try:
        from openai import OpenAI
    except ImportError as e:
        messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 openai 库")
        return
        
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
    progress_window.grab_set()
    
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
            # 从配置文件读取API设置
            api_base_url = self.config.get('VLLM', 'api_base_url', fallback="http://127.0.0.1:8000/v1")
            api_key = self.config.get('VLLM', 'api_key', fallback="EMPTY")
            model_name = self.config.get('VLLM', 'model_name', fallback="/models/Qwen3-VL-8B-Instruct")
            
            # 配置客户端
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            # 初始化时间统计
            start_time = time.time()
            completed_count = 0
            
            # 从配置文件读取生成参数
            max_tokens = self.config.getint('VLLM', 'max_tokens', fallback=1024)
            temperature = self.config.getfloat('VLLM', 'temperature', fallback=0.3)
            top_p = self.config.getfloat('VLLM', 'top_p', fallback=0.9)
            
            for i, segment in enumerate(segments):
                segment_start_time = time.time()
                
                # 提取片段帧
                frames = []
                # 从配置文件读取采样帧数
                max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
                
                # 采样最多max_sample_frames帧以提高性能
                total_frames = segment["end"] - segment["start"] + 1
                sample_count = min(max_sample_frames, total_frames)
                
                if total_frames <= sample_count:
                    indices = list(range(segment["start"], segment["end"] + 1))
                else:
                    indices = np.linspace(segment["start"], segment["end"], sample_count, dtype=int)
                
                # 转换帧为base64格式
                frame_data_urls = []
                for idx in indices:
                    if idx < len(self.processed_frames):
                        # 转为 JPEG 并编码为 base64
                        frame_bgr = cv2.cvtColor(self.processed_frames[idx], cv2.COLOR_RGB2BGR)
                        _, buffer = cv2.imencode(".jpg", frame_bgr)
                        encoded = base64.b64encode(buffer).decode("utf-8")
                        data_url = f"data:image/jpeg;base64,{encoded}"
                        frame_data_urls.append(data_url)
                
                # 如果只有一帧，复制以满足视频处理要求
                if len(frame_data_urls) == 1:
                    frame_data_urls.append(frame_data_urls[0])
                
                # 获取用户自定义的提示词
                user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                if not user_prompt:
                    user_prompt = "详细描述视频画面"
                
                # 构造消息：文本 + 多张图片
                content_list = [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
                
                # 添加所有帧
                for url in frame_data_urls:
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })
                
                messages = [{"role": "user", "content": content_list}]
                
                # 发送请求到vLLM API
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                
                caption = response.choices[0].message.content.strip()
                
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
__all__ = ['_auto_segment_and_recognize_vllm']
