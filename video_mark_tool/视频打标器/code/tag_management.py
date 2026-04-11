# Tag Management Module - 标签管理模块
# 包含标签添加、排除片段、导出和记录保存等功能

import os
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import json
import cv2
import threading
from PIL import Image
import io
import base64
from openai import OpenAI

def add_tag(self):
    # 修改获取标签文本的方式
    tag_text = self.tag_entry.get("1.0", tk.END).strip()
        
    if self.start_frame >= self.end_frame:
        messagebox.showerror("错误", "开始帧不能大于等于结束帧")
        return
        
    # 添加到标记列表
    tag_info = {
        "start": self.start_frame,
        "end": self.end_frame,
        "tag": tag_text
    }
    self.tags.append(tag_info)
    self.regenerate_all_tags_btn.config(state=tk.NORMAL)
    # 更新列表框
    self.tag_listbox.insert(tk.END, f"帧 {self.start_frame}-{self.end_frame}: {tag_text}")
    
    # 启用导出按钮 (如果有至少一个标记)
    if len(self.tags) > 0:
        self.export_btn.config(state=tk.NORMAL)
    
    # 清空输入框
    self.tag_entry.delete("1.0", tk.END)
    
    # 让输入框失去焦点，以便键盘快捷键可以正常使用
    self.root.focus_set()
    
    # 保存当前的结束帧位置
    end_position = self.end_frame
    
    # 清空已选中的开始和结束点
    self.start_frame = 0
    self.end_frame = 0
    
    # 更新标记可视化
    self.draw_tag_markers()
    
    # 将滑块移动到之前设置的结束帧位置
    self.current_frame = end_position
    self.progress.set(self.current_frame)
    self.show_frame()


def exclude_segment(self):
    """标记当前选中的片段为排除片段"""
    if self.start_frame == 0 and self.end_frame == 0:
        messagebox.showerror("错误", "请先设置开始帧和结束帧")
        return
        
    if self.start_frame > self.end_frame:
        messagebox.showerror("错误", "开始帧不能大于结束帧")
        return
        
    # 添加到排除片段列表
    segment_info = {
        "start": self.start_frame,
        "end": self.end_frame
    }
    self.excluded_segments.append(segment_info)
    
    # 清空已选中的开始和结束点
    self.start_frame = 0
    self.end_frame = 0
    
    # 更新标记可视化
    self.draw_tag_markers()
    
    messagebox.showinfo("成功", "已将选中片段标记为排除片段")


def set_export_path(self):
    """设置导出路径"""
    selected_dir = filedialog.askdirectory(title="选择导出文件夹")
    if selected_dir:
        self.export_dir = selected_dir
        messagebox.showinfo("导出路径设置", f"已设置导出路径为：{self.export_dir}")


def export_tags(self):
    if not self.tags:
        messagebox.showerror("错误", "没有标记需要导出")
        return
        
    # 导出目录
    if not self.export_dir:
        self.export_dir = self.config.get('VIDEO', 'export_path', fallback=None)
        messagebox.showerror("错误", "请先设置导出路径")
        return
        
    # 直接使用选中的文件夹
    main_folder = self.export_dir
    
    # 获取导出帧率
    try:
        if self.fps_entry.get() == "原始帧率":
            export_fps = self.fps
        else:
            export_fps = float(self.fps_entry.get())
    except ValueError:
        messagebox.showerror("错误", "请输入有效的帧率数值")
        return
        
    # 创建主文件夹
    
    # 导出每个标记片段
    for i, tag in enumerate(self.tags):
        start_frame = tag["start"]
        end_frame = tag["end"]
        tag_text = tag["tag"]
        
        # 获取第一帧来确定尺寸
        if start_frame < len(self.processed_frames):
            first_frame = self.processed_frames[start_frame]
            height, width = first_frame.shape[:2]
            
            # 生成安全的文件名，移除或替换非法字符
            safe_tag_text = "".join(c for c in tag_text if c.isalnum() or c in (' ', '-', '_')).rstrip()
            # 限制文件名长度
            safe_tag_text = safe_tag_text[:10] if len(safe_tag_text) > 10 else safe_tag_text
            # 替换空格为下划线
            safe_tag_text = safe_tag_text.replace(" ", "_")
            
            # 如果处理后的标签为空，则使用默认名称
            if not safe_tag_text:
                safe_tag_text = "untitled"
            
            # 生成文件名
            filename = f"video_{i+1:03d}_{safe_tag_text}"
            video_path = os.path.join(main_folder, f"{filename}.mp4")
            txt_path = os.path.join(main_folder, f"{filename}.txt")
            
            # 检查文件是否已存在，如果存在则添加序号
            counter = 1
            original_video_path = video_path
            original_txt_path = txt_path
            while os.path.exists(video_path) or os.path.exists(txt_path):
                filename = f"video_{i+1:03d}_{safe_tag_text}_{counter}"
                video_path = os.path.join(main_folder, f"{filename}.mp4")
                txt_path = os.path.join(main_folder, f"{filename}.txt")
                counter += 1
            
            # 视频写入器参数
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(video_path, fourcc, export_fps, (width, height))
            
            # 写入视频帧
            for frame_num in range(start_frame, min(end_frame + 1, len(self.processed_frames))):
                # 将 RGB 转换回 BGR
                frame_bgr = cv2.cvtColor(self.processed_frames[frame_num], cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
                    
            out.release()
            
            # 创建标签文件
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(tag_text)
    
    #messagebox.showinfo("完成", f"已导出 {len(self.tags)} 个标记片段到：{main_folder}")


def load_tag_records(self):
    """从文件加载标记记录"""
    if not self.video_path:
        messagebox.showerror("错误", "请先加载视频文件")
        return
        
    # 生成记录文件路径
    record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
    
    if not os.path.exists(record_file):
        messagebox.showerror("错误", f"未找到标记记录文件：{record_file}")
        return
        
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 验证视频文件是否匹配
        if data.get("video_name") != os.path.basename(self.video_path):
            if not messagebox.askyesno("警告", "记录文件与当前视频不匹配，是否仍要加载？"):
                return
                
        # 验证帧数是否匹配
        if data.get("total_frames") != self.total_frames:
            if not messagebox.askyesno("警告", "视频帧数与记录不匹配，是否仍要加载？"):
                return
        
        # 清空现有标记
        self.tags.clear()
        self.excluded_segments.clear()
        self.tag_listbox.delete(0, tk.END)
        
        # 加载标记
        for tag in data.get("tags", []):
            self.tags.append({
                "start": tag["start"],
                "end": tag["end"],
                "tag": tag["tag"]
            })
            self.tag_listbox.insert(tk.END, f"帧 {tag['start']}-{tag['end']}: {tag['tag']}")
            
        # 加载排除片段
        for segment in data.get("excluded_segments", []):
            self.excluded_segments.append({
                "start": segment["start"],
                "end": segment["end"]
            })
        
        # 更新 UI 状态
        if len(self.tags) > 0:
            self.export_btn.config(state=tk.NORMAL)
            
        # 更新标记可视化
        self.draw_tag_markers()
        
        messagebox.showinfo("成功", f"已加载 {len(self.tags)} 个标记记录")
        
    except Exception as e:
        messagebox.showerror("错误", f"加载标记记录失败：{str(e)}")


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
            
            # 调用 AI 生成新标签
            new_caption = self._generate_single_tag_caption()
            
            if new_caption:  # 如果成功生成了新标签
                # 创建新的标签信息并添加到标签列表
                new_tag_info = {
                    "start": start_frame,
                    "end": end_frame,
                    "tag": new_caption
                }
                self.tags.append(new_tag_info)
                print(f"已添加新标签：{new_caption}")
                # 更新列表框中的显示
                self.root.after(0, lambda s=start_frame, e=end_frame, c=new_caption: 
                               self.tag_listbox.insert(tk.END, f"帧 {s}-{e}: {c}"))
                # 清空已选中的开始和结束点
                self.start_frame = 0
                self.end_frame = 0
        
        # 完成后更新 UI
        def finish_regeneration():
            messagebox.showinfo("完成", "所有标签重新生成完成")
            progress_window.destroy()
        
        self.root.after(0, finish_regeneration)

        self.export_tags()  # 启用导出按钮
        
    except Exception as e:
        def show_error():
            messagebox.showerror("错误", f"重新生成标签失败：{str(e)}")
            progress_window.destroy()
        self.root.after(0, show_error)


def _generate_single_tag_caption(self):
    """为单个标签生成 AI 描述"""
    try:
        # 获取选中的视频片段帧
        if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
            # 从处理后的帧中提取视频片段
            frames = []
            # 从配置文件读取采样帧数
            max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
            # 采样最多 max_sample_frames 帧以提高性能
            total_frames = self.end_frame - self.start_frame + 1
            sample_count = min(max_sample_frames, total_frames)
            
            if total_frames <= sample_count:
                indices = list(range(self.start_frame, self.end_frame + 1))
            else:
                indices = list(map(int, [self.start_frame + i * (total_frames - 1) / (sample_count - 1) for i in range(sample_count)]))
            
            for i in indices:
                if i < len(self.processed_frames):
                    # 转换为 PIL Image
                    frame_rgb = self.processed_frames[i]
                    pil_frame = Image.fromarray(frame_rgb)
                    frames.append(pil_frame)
            
            # 如果只有一帧，复制以满足视频处理要求
            if len(frames) == 1:
                frames.append(frames[0])

            # 从配置文件读取 LLM API 设置
            api_base_url = self.config.get('LLM', 'api_base_url', fallback='http://127.0.0.1:1234/v1')
            api_key = self.config.get('LLM', 'api_key', fallback='ollama')
            model_name = self.config.get('LLM', 'model_name', fallback='qwen3-vl:30b')

            # 从配置文件读取生成参数
            max_new_tokens = self.config.getint('LLM', 'max_new_tokens', fallback=300000)
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
                """将 PIL 图像转换为 base64 编码"""
                # 调整图片大小
                max_size = (720, 720)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # 转换图片为 base64 格式
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
                data_url = f"data:image/png;base64,{encoded}"
                
                return data_url
            
            def generate_caption(frames, prompt_text=None):
                """通过 OpenAI 兼容 API 为多个帧生成统一描述"""
                # 转换所有帧为 base64
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
                max_attempts = 10  # 最多尝试 10 次
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
                    
                    # 检查描述是否为空或少于 50 个字
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
            caption = generate_caption(frames, user_prompt)
            
            return caption
        else:
            return None
    except Exception as e:
        print(f"生成单个标签时出错：{str(e)}")
        return None


def save_tag_records(self):
    """保存标记记录到文件"""
    if not self.video_path or not self.tags:
        messagebox.showerror("错误", "没有视频或标记需要保存")
        return
        
    # 生成记录文件路径（与视频同目录，同名但扩展名为.json）
    record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
    
    # 准备保存的数据
    data = {
        "video_path": self.video_path,
        "video_name": os.path.basename(self.video_path),
        "total_frames": self.total_frames,
        "fps": self.fps,
        "tags": self.tags,
        "excluded_segments": self.excluded_segments
    }
    
    try:
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("成功", f"标记记录已保存到：{record_file}")
    except Exception as e:
        messagebox.showerror("错误", f"保存标记记录失败：{str(e)}")


__all__ = [
    'add_tag',
    'exclude_segment',
    'set_export_path',
    'export_tags',
    'load_tag_records',
    'regenerate_all_tags',
    '_regenerate_all_tags_thread',
    '_generate_single_tag_caption',
    'save_tag_records'
]
