# This is a method from class VideoTagger
import os
import tkinter as tk
from tkinter import  messagebox, ttk
from PIL import Image
import threading

def _auto_segment_and_recognize_local(self):
    """使用本地模型自动按5秒分段并使用AI识别生成标签"""
    if not self.model_loaded:
        # 如果模型未加载，则自动加载模型
        try:
            # 检查是否安装了必要的库
            import torch
            from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
        except ImportError as e:
            messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 transformers 和 torch 库")
            return
        
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
        
        tk.Label(loading_window, text="正在加载模型...", font=self.font).pack(pady=20)
        self.root.update()
        
        try:
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
            
            loading_window.destroy()
            
        except Exception as e:
            messagebox.showerror("错误", f"模型加载失败: {str(e)}")
            loading_window.destroy()
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
            # 重新导入必要的库，解决变量作用域问题
            import torch
            from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
            import numpy as np
            import time
            
            # 存储需要重新处理的片段
            retry_segments = []
            
            # 初始化时间统计
            start_time = time.time()
            completed_count = 0
            
            # 从配置文件读取生成参数
            max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=1024)
            temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.6)
            top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
            retry_max_new_tokens = self.config.getint('MODEL', 'retry_max_new_tokens', fallback=512)
            
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
                
                for idx in indices:
                    if idx < len(self.processed_frames):
                        # 转换为PIL Image
                        frame_rgb = self.processed_frames[idx]
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
                
                # 检查生成的提示词是否超过300字符，如果超过则需要重新生成
                if len(caption) > 300:
                    retry_segments.append((i, segment, frames, user_prompt))
                
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
            
            # 处理需要重新生成的片段
            if retry_segments:
                retry_window = tk.Toplevel(self.root)
                retry_window.title("重新生成被判断过长的提示词")
                retry_window.geometry("400x150")
                retry_window.transient(self.root)
                retry_window.grab_set()
                
                # 居中显示
                retry_window.update_idletasks()
                x = (retry_window.winfo_screenwidth() // 2) - (400 // 2)
                y = (retry_window.winfo_screenheight() // 2) - (150 // 2)
                retry_window.geometry(f"400x150+{x}+{y}")
                
                tk.Label(retry_window, text="正在重新生成长提示词，请稍候...", font=self.font).pack(pady=10)
                
                # 创建进度条
                retry_progress_bar = ttk.Progressbar(retry_window, mode='determinate')
                retry_progress_bar.pack(pady=10, padx=20, fill=tk.X)
                retry_progress_bar['maximum'] = len(retry_segments)
                
                retry_progress_label = tk.Label(retry_window, text="0%", font=self.font)
                retry_progress_label.pack()
                
                for i, (original_index, segment, frames, user_prompt) in enumerate(retry_segments):
                    # 使用更具体的提示词重新生成
                    retry_prompt = user_prompt + " 请用简洁明了的语言描述，不超过300字。"
                    
                    # 构建对话
                    retry_conversation = [{
                        "role": "user",
                        "content": [
                            {"type": "video", "video": frames},
                            {"type": "text", "text": retry_prompt}
                        ]
                    }]
                    
                    # 应用模板
                    retry_text_prompt = self.processor.apply_chat_template(
                        retry_conversation,
                        tokenize=False,
                        add_generation_prompt=True
                    )
                    
                    # 处理输入
                    retry_inputs = self.processor(
                        text=retry_text_prompt,
                        videos=[frames],
                        return_tensors="pt"
                    )
                    
                    # 移动到设备
                    retry_inputs = {k: v.to(self.model.device) for k, v in retry_inputs.items()}
                    
                    # 生成输出
                    with torch.no_grad():
                        retry_outputs = self.model.generate(
                            **retry_inputs,
                            max_new_tokens=retry_max_new_tokens,  # 减少最大token数以控制长度
                            do_sample=True,
                            temperature=temperature,
                            top_p=top_p
                        )
                    
                    # 解码输出
                    retry_input_ids_len = retry_inputs["input_ids"].shape[1]
                    retry_caption = self.tokenizer.decode(
                        retry_outputs[0, retry_input_ids_len:],
                        skip_special_tokens=True
                    )
                    retry_caption = retry_caption.strip()
                    
                    # 更新标记列表中的内容
                    tag_index = original_index  # 原始索引保持不变
                    if tag_index < len(self.tags):
                        self.tags[tag_index]["tag"] = retry_caption
                        # 更新列表框显示
                        self.tag_listbox.delete(tag_index)
                        self.tag_listbox.insert(tag_index, f"帧 {segment['start']}-{segment['end']}: {retry_caption}")
                    
                    # 更新进度
                    retry_progress_bar['value'] = i + 1
                    retry_progress_percent = int((i + 1) / len(retry_segments) * 100)
                    retry_progress_label.config(text=f"{retry_progress_percent}%")
                    retry_window.update()
                
                retry_window.destroy()
            
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
