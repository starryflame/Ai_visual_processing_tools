# This is a method from class VideoTagger
import cv2
import tkinter as tk
from tkinter import messagebox
import numpy as np
import base64

def _generate_ai_caption_vllm(self):
    """使用vLLM API生成标签"""
    try:
        from openai import OpenAI
    except ImportError as e:
        messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 openai 库")
        return
        
    # 显示加载提示
    loading_window = tk.Toplevel(self.root)
    loading_window.title("AI处理中")
    loading_window.geometry("300x150")
    loading_window.transient(self.root)
    loading_window.grab_set()
    
    # 将窗口居中显示
    loading_window.update_idletasks()
    x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
    y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
    loading_window.geometry(f"300x100+{x}+{y}")
    
    tk.Label(loading_window, text="正在通过vLLM API生成标签...", font=self.font).pack(pady=20)
    self.root.update()
    
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
        
        # 获取选中的视频片段帧
        if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
            # 从处理后的帧中提取视频片段
            frames = []
            # 从配置文件读取采样帧数
            max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
            
            # 采样最多max_sample_frames帧以提高性能
            total_frames = self.end_frame - self.start_frame + 1
            sample_count = min(max_sample_frames, total_frames)
            
            if total_frames <= sample_count:
                indices = list(range(self.start_frame, self.end_frame + 1))
            else:
                indices = np.linspace(self.start_frame, self.end_frame, sample_count, dtype=int)
            
            # 转换帧为base64格式
            frame_data_urls = []
            for i in indices:
                if i < len(self.processed_frames):
                    # 转为 JPEG 并编码为 base64
                    frame_bgr = cv2.cvtColor(self.processed_frames[i], cv2.COLOR_RGB2BGR)
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
            
            # 从配置文件读取生成参数
            max_tokens = self.config.getint('VLLM', 'max_tokens', fallback=1024)
            temperature = self.config.getfloat('VLLM', 'temperature', fallback=0.3)
            top_p = self.config.getfloat('VLLM', 'top_p', fallback=0.9)
            
            # 发送请求到vLLM API
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            
            caption = response.choices[0].message.content.strip()
            
            # 添加到预设列表
            # 使用第一帧作为缩略图
            thumbnail_frame = self.processed_frames[self.start_frame].copy()
            self.caption_presets.append({
                "caption": caption,
                "image": thumbnail_frame
            })
            
            # 创建新的预设项显示
            self.create_preset_item(len(self.caption_presets) - 1, caption, thumbnail_frame)
            
            messagebox.showinfo("成功", f"AI已生成标签并添加到预设列表:\n\n{caption}")
        else:
            messagebox.showerror("错误", "无法获取选中的视频片段")
            
    except Exception as e:
        messagebox.showerror("错误", f"AI标签生成失败: {str(e)}")
    finally:
        loading_window.destroy()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['_generate_ai_caption_vllm']
