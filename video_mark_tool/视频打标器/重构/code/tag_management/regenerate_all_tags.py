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
def regenerate_all_tags(self):
    """重新生成所有标签"""
    if not self.tags:
        messagebox.showinfo("提示", "没有标签需要重新生成")
        return
    

    # 启动新线程执行重新生成任务
    thread = threading.Thread(target=self._regenerate_all_tags_thread)
    thread.daemon = True
    thread.start()

def _regenerate_all_tags_thread(self):
    """在新线程中执行重新生成所有标签的任务"""
    # 显示进度窗口
    progress_window = tk.Toplevel(self.root)
    progress_window.title("重新生成标签")
    progress_window.geometry("400x100")
    progress_window.transient(self.root)
    
    # 将窗口居中显示
    progress_window.update_idletasks()
    x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
    y = (progress_window.winfo_screenheight() // 2) - (100 // 2)
    progress_window.geometry(f"400x100+{x}+{y}")
    
    tk.Label(progress_window, text="正在重新生成所有标签...", font=self.font).pack(pady=20)
    
    try:
        original_tags = self.tags.copy()  # 保存原始标签
        
        # 清空原标签列表和列表框显示
        self.tags.clear()
        self.root.after(0, lambda: self.tag_listbox.delete(0, tk.END))
        
        for idx, tag_info in enumerate(original_tags):
            start_frame = tag_info["start"]
            end_frame = tag_info["end"]
            print(f"正在处理帧 {start_frame}-{end_frame}")
            # 设置当前帧范围
            self.start_frame = start_frame
            self.end_frame = end_frame
            
            # 调用AI生成新标签
            new_caption = self._generate_single_tag_caption()
            
            if new_caption:  # 如果成功生成了新标签
                # 创建新的标签信息并添加到标签列表
                new_tag_info = {
                    "start": start_frame,
                    "end": end_frame,
                    "tag": new_caption
                }
                self.tags.append(new_tag_info)
                print(f"已添加新标签: {new_caption}")
                # 更新列表框中的显示
                self.root.after(0, lambda s=start_frame, e=end_frame, c=new_caption: 
                               self.tag_listbox.insert(tk.END, f"帧 {s}-{e}: {c}"))
                # 清空已选中的开始和结束点
                self.start_frame = 0
                self.end_frame = 0
        
        # 完成后更新UI
        def finish_regeneration():
            messagebox.showinfo("完成", "所有标签重新生成完成")
            progress_window.destroy()
        
        self.root.after(0, finish_regeneration)
        
    except Exception as e:
        def show_error():
            messagebox.showerror("错误", f"重新生成标签失败: {str(e)}")
            progress_window.destroy()
        self.root.after(0, show_error)

def _generate_single_tag_caption(self):
    """为单个标签生成AI描述"""
    try:
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
                indices = list(map(int, [self.start_frame + i * (total_frames - 1) / (sample_count - 1) for i in range(sample_count)]))
            
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

                    caption = response.choices[0].message.content.strip()
                    
                    # 检查是否包含过滤词
                    contains_filter_word = False
                    caption_lower = caption.lower()
                    for word in filter_words:
                        if word in caption_lower:
                            contains_filter_word = True
                            break
                    
                    # 如果包含过滤词且不是最后一次尝试，则重新生成
                    if contains_filter_word and attempt < max_attempts - 1:
                        continue
                    
                    # 检查描述是否为空或少于50个字
                    if len(caption) < 50:
                        # 如果不是最后一次尝试，继续循环重新生成
                        if attempt < max_attempts - 1:
                            continue
                        else:
                            # 最后一次尝试后仍然太短，则返回默认提示
                            return "视频描述内容过短，无法提供有效描述"

                    # 如果不包含过滤词且长度符合要求，则返回结果
                    if not contains_filter_word:
                        return caption
                
                # 如果所有尝试都包含过滤词，则在最后返回时移除过滤词
                for word in filter_words:
                    caption = caption.replace(word, '')
                return caption.strip() or "视频描述内容已被过滤"
            
            # 获取用户自定义的提示词
            user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
            
            # 生成描述
            caption = generate_caption_with_ollama(frames, user_prompt)
            
            return caption
        else:
            return None
    except Exception as e:
        print(f"生成单个标签时出错: {str(e)}")
        return None

__all__ = ['regenerate_all_tags', '_regenerate_all_tags_thread', '_generate_single_tag_caption']