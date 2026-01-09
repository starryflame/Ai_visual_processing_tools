# This is a method from class VideoTagger
import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image
import torch
from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
import numpy as np


def _generate_ai_caption_local(self):
    """使用本地模型生成标签"""
    # 显示加载提示
    loading_window = tk.Toplevel(self.root)
    loading_window.title("AI处理中")
    loading_window.geometry("300x100")
    loading_window.transient(self.root)
    loading_window.grab_set()
    
    # 将窗口居中显示
    loading_window.update_idletasks()
    x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
    y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
    loading_window.geometry(f"300x100+{x}+{y}")
    
    tk.Label(loading_window, text="正在加载模型并生成标签...", font=self.font).pack(pady=20)
    self.root.update()
    
    try:
        # 检查模型是否已加载
        if not self.model_loaded:
            # 从配置文件读取模型路径
            model_path = self.config.get('MODEL', 'qwen_vl_model_path', fallback=r"J:\models\LLM\Qwen-VL\Qwen3-VL-4B-Instruct")
            
            if not os.path.exists(model_path):
                messagebox.showerror("错误", f"模型路径不存在: {model_path}\n请确认模型已下载并放置在正确位置")
                loading_window.destroy()
                return
            
            # 从配置文件读取模型精度设置
            torch_dtype_str = self.config.get('MODEL', 'torch_dtype', fallback='fp32')
            if torch_dtype_str == 'fp16':
                torch_dtype = torch.float16
            elif torch_dtype_str == 'bf16':
                torch_dtype = torch.bfloat16
            else:
                torch_dtype = torch.float32
            
            # 加载模型
            self.model = AutoModelForVision2Seq.from_pretrained(
                model_path,
                device_map="auto",
                trust_remote_code=True,
                torch_dtype=torch_dtype
            ).eval()
            self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            self.model_loaded = True
        
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
            
            for i in indices:
                if i < len(self.processed_frames):
                    # 转换为PIL Image
                    frame_rgb = self.processed_frames[i]
                    pil_frame = Image.fromarray(frame_rgb)
                    frames.append(pil_frame)
            
            # 如果只有一帧，复制以满足视频处理要求
            if len(frames) == 1:
                frames.append(frames[0])
            
            # 获取用户自定义的提示词
            user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
            if not user_prompt:
                user_prompt = "详细描述视频画面"
            
            # 构建对话
            conversation = [{
                "role": "user",
                "content": [
                    {"type": "video", "video": frames},
                    {"type": "text", "text": user_prompt}
                ]
            }]
            
            # 应用模板
            text_prompt = self.processor.apply_chat_template(
                conversation,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # 处理输入
            inputs = self.processor(
                text=text_prompt,
                videos=[frames],
                return_tensors="pt"
            )
            
            # 移动到设备
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
            
            # 从配置文件读取生成参数
            max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=1024)
            temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.6)
            top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
            
            # 生成输出
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=True,
                    temperature=temperature,
                    top_p=top_p
                )
            
            # 解码输出
            input_ids_len = inputs["input_ids"].shape[1]
            caption = self.tokenizer.decode(
                outputs[0, input_ids_len:],
                skip_special_tokens=True
            )
            caption = caption.strip()
            
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
__all__ = ['_generate_ai_caption_local']
