import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
import cv2
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import threading
# 添加subprocess模块用于调用FFmpeg
import subprocess
import shutil

class MediaConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("全能媒体格式转换器")
        self.root.geometry("1200x900")
        
        self.selected_path = tk.StringVar()
        self.target_format = tk.StringVar(value="jpg")
        self.convert_type = tk.StringVar(value="image")  # 新增：转换类型
        self.convert_video_to_gif = tk.BooleanVar(value=False)
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="就绪")
        # 添加帧率变量，默认值为5
        self.gif_fps = tk.StringVar(value="5")
        # 添加分辨率变量，默认值为原始分辨率
        self.gif_width = tk.StringVar(value="原始")
        self.gif_height = tk.StringVar(value="原始")
        
        # 新增：音频格式选项
        self.audio_formats = ["mp3", "wav", "flac", "aac", "ogg"]
        self.image_formats = ["jpg", "png", "bmp", "tiff", "webp"]
        self.video_formats = ["mp4", "avi", "mov", "mkv"]
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="全能媒体格式转换器", font=("微软雅黑", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 路径选择
        path_frame = ttk.LabelFrame(main_frame, text="选择路径", padding="10")
        path_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Entry(path_frame, textvariable=self.selected_path, width=80).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(path_frame, text="浏览文件", command=self.select_file).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(path_frame, text="浏览文件夹", command=self.select_folder).grid(row=0, column=2)
        
        # 转换类型选择
        type_frame = ttk.LabelFrame(main_frame, text="转换类型", padding="10")
        type_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 使用Radiobutton选择转换类型
        ttk.Radiobutton(type_frame, text="图片转换", variable=self.convert_type, value="image", command=self.on_type_change).grid(row=0, column=0, padx=(10, 20))
        ttk.Radiobutton(type_frame, text="视频转换", variable=self.convert_type, value="video", command=self.on_type_change).grid(row=0, column=1, padx=(10, 20))
        ttk.Radiobutton(type_frame, text="音频转换", variable=self.convert_type, value="audio", command=self.on_type_change).grid(row=0, column=2, padx=(10, 20))
        ttk.Radiobutton(type_frame, text="全部转换", variable=self.convert_type, value="all", command=self.on_type_change).grid(row=0, column=3, padx=(10, 20))
        
        # 转换选项
        options_frame = ttk.LabelFrame(main_frame, text="转换选项", padding="10")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 格式选择
        format_frame = ttk.Frame(options_frame)
        format_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(format_frame, text="目标格式:").grid(row=0, column=0, sticky=tk.W)
        self.format_combo = ttk.Combobox(format_frame, textvariable=self.target_format, values=self.image_formats, state="readonly", width=15)
        self.format_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        self.format_combo.bind("<<ComboboxSelected>>", self.on_format_change)
        
        # 视频转GIF选项
        self.gif_options_frame = ttk.Frame(options_frame)
        self.gif_options_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Checkbutton(self.gif_options_frame, text="视频转GIF", variable=self.convert_video_to_gif).grid(row=0, column=0, sticky=tk.W, pady=(10, 0))
        
        # GIF帧率设置
        ttk.Label(self.gif_options_frame, text="GIF帧率:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        gif_fps_entry = ttk.Entry(self.gif_options_frame, textvariable=self.gif_fps, width=10)
        gif_fps_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Label(self.gif_options_frame, text="fps").grid(row=1, column=2, sticky=tk.W, pady=(10, 0))
        
        # GIF分辨率设置
        ttk.Label(self.gif_options_frame, text="GIF宽度:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        gif_width_entry = ttk.Entry(self.gif_options_frame, textvariable=self.gif_width, width=10)
        gif_width_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Label(self.gif_options_frame, text="像素 (输入'原始'保持原尺寸)").grid(row=2, column=2, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(self.gif_options_frame, text="GIF高度:").grid(row=3, column=0, sticky=tk.W, pady=(5, 0))
        gif_height_entry = ttk.Entry(self.gif_options_frame, textvariable=self.gif_height, width=10)
        gif_height_entry.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        ttk.Label(self.gif_options_frame, text="像素 (输入'原始'保持原尺寸)").grid(row=3, column=2, sticky=tk.W, pady=(5, 0))
        
        # 隐藏GIF选项，因为默认情况下视频转换不是GIF
        self.gif_options_frame.grid_remove()
        
        # 操作按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=(0, 10))
        
        self.convert_btn = ttk.Button(button_frame, text="开始转换", command=self.start_conversion)
        self.convert_btn.grid(row=0, column=0, padx=(0, 10))
        
        ttk.Button(button_frame, text="清空日志", command=self.clear_log).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(button_frame, text="退出", command=self.root.quit).grid(row=0, column=2)
        
        # 进度条
        progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(progress_frame, textvariable=self.status_var).grid(row=1, column=0, sticky=tk.W)
        
        # 日志框
        log_frame = ttk.LabelFrame(main_frame, text="日志", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = tk.Text(log_frame, height=15, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        path_frame.columnconfigure(0, weight=1)
        type_frame.columnconfigure(0, weight=1)
        type_frame.columnconfigure(1, weight=1)
        type_frame.columnconfigure(2, weight=1)
        type_frame.columnconfigure(3, weight=1)
        options_frame.columnconfigure(0, weight=1)
        format_frame.columnconfigure(1, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 初始化界面状态
        self.update_format_options()
        
    def on_type_change(self):
        """当转换类型改变时更新界面"""
        self.update_format_options()
        
    def on_format_change(self, event=None):
        """当格式改变时更新界面"""
        if self.target_format.get() in ["mp4", "avi", "mov", "mkv"]:
            self.gif_options_frame.grid()
        else:
            self.gif_options_frame.grid_remove()
    
    def update_format_options(self):
        """根据转换类型更新格式选项"""
        convert_type = self.convert_type.get()
        if convert_type == "image":
            self.format_combo['values'] = self.image_formats
            self.target_format.set("jpg")
        elif convert_type == "video":
            self.format_combo['values'] = self.video_formats
            self.target_format.set("mp4")
        elif convert_type == "audio":
            self.format_combo['values'] = self.audio_formats
            self.target_format.set("mp3")
        elif convert_type == "all":
            all_formats = self.image_formats + self.video_formats + self.audio_formats
            self.format_combo['values'] = all_formats
            self.target_format.set("jpg")
        
        # 更新GIF选项显示
        if self.target_format.get() in ["gif"] or self.convert_video_to_gif.get():
            self.gif_options_frame.grid()
        else:
            self.gif_options_frame.grid_remove()
    
    def select_file(self):
        convert_type = self.convert_type.get()
        
        # 根据转换类型过滤文件
        if convert_type == "image":
            file_types = [
                ("图片文件", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.webp"),
                ("所有支持的文件", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.webp;*.mp4;*.avi;*.mov;*.mkv;*.mp3;*.wav;*.flac;*.aac;*.ogg"),
                ("所有文件", "*.*")
            ]
        elif convert_type == "video":
            file_types = [
                ("视频文件", "*.mp4;*.avi;*.mov;*.mkv"),
                ("所有支持的文件", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.webp;*.mp4;*.avi;*.mov;*.mkv;*.mp3;*.wav;*.flac;*.aac;*.ogg"),
                ("所有文件", "*.*")
            ]
        elif convert_type == "audio":
            file_types = [
                ("音频文件", "*.mp3;*.wav;*.flac;*.aac;*.ogg"),
                ("所有支持的文件", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.webp;*.mp4;*.avi;*.mov;*.mkv;*.mp3;*.wav;*.flac;*.aac;*.ogg"),
                ("所有文件", "*.*")
            ]
        else:  # all
            file_types = [
                ("所有支持的文件", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.webp;*.mp4;*.avi;*.mov;*.mkv;*.mp3;*.wav;*.flac;*.aac;*.ogg"),
                ("图片文件", "*.jpg;*.jpeg;*.png;*.bmp;*.tiff;*.webp"),
                ("视频文件", "*.mp4;*.avi;*.mov;*.mkv"),
                ("音频文件", "*.mp3;*.wav;*.flac;*.aac;*.ogg"),
                ("所有文件", "*.*")
            ]
        
        file_path = filedialog.askopenfilename(
            title="选择文件",
            filetypes=file_types
        )
        if file_path:
            self.selected_path.set(file_path)
            
    def select_folder(self):
        folder_path = filedialog.askdirectory(title="选择文件夹")
        if folder_path:
            self.selected_path.set(folder_path)
            
    def log_message(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def start_conversion(self):
        if not self.selected_path.get():
            messagebox.showerror("错误", "请选择文件或文件夹")
            return
            
        if not os.path.exists(self.selected_path.get()):
            messagebox.showerror("错误", "选择的路径不存在")
            return
            
        # 在新线程中执行转换，避免界面冻结
        thread = threading.Thread(target=self.convert_media)
        thread.daemon = True
        thread.start()
        
    def convert_media(self):
        try:
            self.convert_btn.config(state=tk.DISABLED)
            self.status_var.set("正在扫描文件...")
            self.progress_var.set(0)
            
            path = self.selected_path.get()
            files_to_convert = []
            
            # 获取需要转换的文件列表
            if os.path.isfile(path):
                files_to_convert.append(path)
                output_base_dir = None
            else:
                # 为转换后的文件创建新的输出目录
                output_base_dir = os.path.join(os.path.dirname(path), f"{os.path.basename(path)}_converted")
                if not os.path.exists(output_base_dir):
                    os.makedirs(output_base_dir)
                    
                for root, dirs, files in os.walk(path):
                    for file in files:
                        files_to_convert.append(os.path.join(root, file))
                        
            total_files = len(files_to_convert)
            if total_files == 0:
                self.log_message("未找到任何文件")
                self.status_var.set("完成")
                self.convert_btn.config(state=tk.NORMAL)
                return
                
            self.log_message(f"找到 {total_files} 个文件")
            
            # 处理每个文件
            converted_count = 0
            for i, file_path in enumerate(files_to_convert):
                try:
                    self.status_var.set(f"正在处理: {os.path.basename(file_path)} ({i+1}/{total_files})")
                    self.progress_var.set((i / total_files) * 100)
                    
                    # 计算输出文件路径
                    if output_base_dir:
                        # 保持原有的文件夹结构
                        relative_path = os.path.relpath(file_path, path)
                        output_file_path = os.path.join(output_base_dir, relative_path)
                        output_dir = os.path.dirname(output_file_path)
                        if not os.path.exists(output_dir):
                            os.makedirs(output_dir)
                    else:
                        output_file_path = None  # 单个文件的情况将在转换函数中处理
                        
                    # 根据转换类型处理文件
                    convert_type = self.convert_type.get()
                    success = False
                    
                    if convert_type in ["image", "all"] and self.is_image_file(file_path):
                        self.convert_image(file_path, output_file_path)
                        success = True
                    elif convert_type in ["video", "all"] and self.is_video_file(file_path):
                        if self.convert_video_to_gif.get() and self.target_format.get() == "gif":
                            self.convert_video_to_gif_format(file_path, output_file_path)
                        else:
                            self.convert_video(file_path, output_file_path)
                        success = True
                    elif convert_type in ["audio", "all"] and self.is_audio_file(file_path):
                        self.convert_audio(file_path, output_file_path)
                        success = True
                    elif convert_type == "all":  # 如果选择了"全部"但文件类型不符合当前目标格式
                        if self.is_image_file(file_path) and self.target_format.get() in self.image_formats:
                            self.convert_image(file_path, output_file_path)
                            success = True
                        elif self.is_video_file(file_path) and self.target_format.get() in self.video_formats:
                            self.convert_video(file_path, output_file_path)
                            success = True
                        elif self.is_audio_file(file_path) and self.target_format.get() in self.audio_formats:
                            self.convert_audio(file_path, output_file_path)
                            success = True
                    
                    if success:
                        converted_count += 1
                        self.log_message(f"已转换: {file_path}")
                    else:
                        self.log_message(f"跳过文件 (格式不匹配): {file_path}")
                        
                except Exception as e:
                    self.log_message(f"处理失败 {file_path}: {str(e)}")
                    
                # 更新UI
                self.root.update_idletasks()
                
            self.progress_var.set(100)
            self.status_var.set("转换完成")
            self.log_message(f"共处理 {total_files} 个文件，成功转换 {converted_count} 个文件")
            if output_base_dir:
                self.log_message(f"输出目录: {output_base_dir}")
            messagebox.showinfo("完成", f"文件转换已完成\n共处理 {total_files} 个文件，成功转换 {converted_count} 个文件")
            
        except Exception as e:
            self.log_message(f"转换过程中出现错误: {str(e)}")
            messagebox.showerror("错误", f"转换过程中出现错误:\n{str(e)}")
        finally:
            self.convert_btn.config(state=tk.NORMAL)
            
    def is_image_file(self, file_path):
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp']
        return any(file_path.lower().endswith(ext) for ext in image_extensions)
        
    def is_video_file(self, file_path):
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        return any(file_path.lower().endswith(ext) for ext in video_extensions)
        
    def is_audio_file(self, file_path):
        audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg']
        return any(file_path.lower().endswith(ext) for ext in audio_extensions)
        
    def convert_image(self, file_path, output_path=None):
        try:
            with Image.open(file_path) as img:
                # 如果图像是RGBA模式且目标格式是JPEG，则转换为RGB
                if img.mode == 'RGBA' and self.target_format.get().lower() in ['jpg', 'jpeg']:
                    img = img.convert('RGB')
                    
                # 构建输出文件路径
                if output_path:
                    base_name = os.path.splitext(output_path)[0]
                    output_path = f"{base_name}.{self.target_format.get().lower()}"
                else:
                    base_name = os.path.splitext(file_path)[0]
                    output_path = f"{base_name}_converted.{self.target_format.get().lower()}"
                
                # 确保输出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # 保存图像
                if self.target_format.get().lower() == 'webp':
                    img.save(output_path, 'WEBP')
                else:
                    img.save(output_path)
                    
        except Exception as e:
            raise Exception(f"图像转换失败: {str(e)}")
            
    def convert_video(self, file_path, output_path=None):
        """转换视频格式"""
        try:
            # 构建输出文件路径
            if output_path:
                base_name = os.path.splitext(output_path)[0]
                output_path = f"{base_name}.{self.target_format.get().lower()}"
            else:
                base_name = os.path.splitext(file_path)[0]
                output_path = f"{base_name}_converted.{self.target_format.get().lower()}"
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 检查FFmpeg是否可用
            if not self.is_ffmpeg_available():
                raise Exception("FFmpeg不可用，请安装FFmpeg")
            
            # 使用FFmpeg转换视频格式
            cmd = [
                "ffmpeg",
                "-i", file_path,
                "-c:v", "libx264",  # 使用H.264编码
                "-c:a", "aac",      # 使用AAC音频编码
                "-strict", "experimental",
                "-y",               # 覆盖输出文件
                output_path
            ]
            
            result = subprocess.run(cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            
            if result.returncode != 0:
                raise Exception(f"视频转换失败: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"视频转换失败: {str(e)}")
    
    def convert_audio(self, file_path, output_path=None):
        """转换音频格式"""
        try:
            # 构建输出文件路径
            if output_path:
                base_name = os.path.splitext(output_path)[0]
                output_path = f"{base_name}.{self.target_format.get().lower()}"
            else:
                base_name = os.path.splitext(file_path)[0]
                output_path = f"{base_name}_converted.{self.target_format.get().lower()}"
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 检查FFmpeg是否可用
            if not self.is_ffmpeg_available():
                raise Exception("FFmpeg不可用，请安装FFmpeg")
            
            # 使用FFmpeg转换音频格式
            # 根据目标格式设置适当的编解码器
            target_format = self.target_format.get().lower()
            if target_format == "mp3":
                cmd = [
                    "ffmpeg",
                    "-i", file_path,
                    "-c:a", "libmp3lame",  # 使用LAME MP3编码器
                    "-b:a", "320k",       # 设置比特率为320kbps
                    "-y",                 # 覆盖输出文件
                    output_path
                ]
            elif target_format == "flac":
                cmd = [
                    "ffmpeg",
                    "-i", file_path,
                    "-c:a", "flac",       # 使用FLAC编码器
                    "-compression_level", "5",  # 设置压缩级别
                    "-y",                 # 覆盖输出文件
                    output_path
                ]
            elif target_format == "aac":
                cmd = [
                    "ffmpeg",
                    "-i", file_path,
                    "-c:a", "aac",        # 使用AAC编码器
                    "-b:a", "256k",       # 设置比特率为256kbps
                    "-y",                 # 覆盖输出文件
                    output_path
                ]
            elif target_format == "wav":
                cmd = [
                    "ffmpeg",
                    "-i", file_path,
                    "-c:a", "pcm_s16le",  # 使用WAV PCM编码
                    "-y",                 # 覆盖输出文件
                    output_path
                ]
            elif target_format == "ogg":
                cmd = [
                    "ffmpeg",
                    "-i", file_path,
                    "-c:a", "libvorbis",  # 使用Vorbis编码器
                    "-q:a", "5",          # 设置质量等级
                    "-y",                 # 覆盖输出文件
                    output_path
                ]
            else:
                # 对于其他未知格式，使用通用方法
                cmd = [
                    "ffmpeg",
                    "-i", file_path,
                    "-c:a", "copy",       # 尝试复制音频流
                    "-strict", "experimental",
                    "-y",                 # 覆盖输出文件
                    output_path
                ]
            
            result = subprocess.run(cmd,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            
            if result.returncode != 0:
                raise Exception(f"音频转换失败: {result.stderr}")
                
        except Exception as e:
            raise Exception(f"音频转换失败: {str(e)}")

    def convert_video_to_gif_format(self, file_path, output_path=None):
        try:
            # 构建输出文件路径
            if output_path:
                base_name = os.path.splitext(output_path)[0]
                output_path = f"{base_name}.gif"
            else:
                base_name = os.path.splitext(file_path)[0]
                output_path = f"{base_name}.gif"
            
            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 检查FFmpeg是否可用
            if not self.is_ffmpeg_available():
                self.log_message("FFmpeg不可用，使用OpenCV方法")
                # 使用原有的OpenCV方法
                self._convert_with_opencv(file_path, output_path)
                return
            
            # 获取用户设置的GIF帧率
            try:
                target_fps = float(self.gif_fps.get())
            except ValueError:
                target_fps = 5.0  # 默认帧率
                self.log_message("无效的帧率值，使用默认值5fps")
            
            # 使用FFmpeg转换视频到GIF
            self._convert_with_ffmpeg(file_path, output_path, target_fps)
                
        except Exception as e:
            raise Exception(f"视频转GIF失败: {str(e)}")

    def is_ffmpeg_available(self):
        """检查FFmpeg是否可用"""
        try:
            subprocess.run(["ffmpeg", "-version"], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL,
                          encoding='utf-8',
                          errors='ignore')
            return True
        except (FileNotFoundError, subprocess.SubprocessError):
            return False

    def _convert_with_ffmpeg(self, input_path, output_path, fps):
        """使用FFmpeg将视频转换为GIF"""
        try:
            # 获取用户设置的分辨率
            width_str = self.gif_width.get()
            height_str = self.gif_height.get()
            
            # 构建缩放参数
            if width_str.lower() == "原始" and height_str.lower() == "原始":
                scale_param = "scale=iw:ih"  # 保持原始分辨率
            elif width_str.lower() == "原始":
                try:
                    height_val = int(height_str)
                    scale_param = f"scale=-1:{height_val}"
                except ValueError:
                    scale_param = "scale=iw:ih"  # 保持原始分辨率
            elif height_str.lower() == "原始":
                try:
                    width_val = int(width_str)
                    scale_param = f"scale={width_val}:-1"
                except ValueError:
                    scale_param = "scale=iw:ih"  # 保持原始分辨率
            else:
                try:
                    width_val = int(width_str) if width_str.isdigit() else -1
                    height_val = int(height_str) if height_str.isdigit() else -1
                    scale_param = f"scale={width_val}:{height_val}"
                except ValueError:
                    scale_param = "scale=iw:ih"  # 保持原始分辨率
            
            # 使用两步法提高GIF质量：先生成调色板，再转换为GIF
            palette_path = output_path + "_palette.png"
            
            # 第一步：生成调色板
            palette_cmd = [
                "ffmpeg",
                "-i", input_path,
                "-vf", f"{scale_param},fps={fps},palettegen",
                "-y",
                palette_path
            ]
            
            palette_result = subprocess.run(palette_cmd,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          text=True,
                                          encoding='utf-8',
                                          errors='ignore')
            
            if palette_result.returncode != 0:
                # 如果调色板生成失败，回退到简单方法
                raise Exception("调色板生成失败，使用基础转换方法")
            
            # 第二步：使用调色板生成高质量GIF
            cmd = [
                "ffmpeg",
                "-i", input_path,
                "-i", palette_path,
                "-lavfi", f"{scale_param},fps={fps} [x]; [x][1:v] paletteuse",
                "-f", "gif",
                "-y",
                output_path
            ]
            
            # 执行FFmpeg命令
            result = subprocess.run(cmd, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True,
                                  encoding='utf-8',
                                  errors='ignore')
            
            # 清理临时调色板文件
            if os.path.exists(palette_path):
                os.remove(palette_path)
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg转换失败: {result.stderr}")
                
        except Exception as e:
            # 如果高级方法失败，尝试简单的转换方法
            self.log_message(f"高质量转换失败: {str(e)}，尝试基础方法")
            self._convert_with_ffmpeg_simple(input_path, output_path, fps, scale_param)

    def _convert_with_ffmpeg_simple(self, input_path, output_path, fps, scale_param):
        """使用FFmpeg的基础GIF转换方法"""
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", f"{scale_param},fps={fps}",
            "-pix_fmt", "rgb24",  # 指定像素格式以改善质量
            "-f", "gif",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True,
                              encoding='utf-8',
                              errors='ignore')
        
        if result.returncode != 0:
            raise Exception(f"FFmpeg基础转换也失败: {result.stderr}")
            
    def _convert_with_opencv(self, file_path, output_path):
        """原有的OpenCV转换方法作为备选方案"""
        # 使用OpenCV读取视频并转换为GIF
        cap = cv2.VideoCapture(file_path)
        
        # 获取视频的基本信息
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # 获取用户设置的GIF帧率
        try:
            target_fps = float(self.gif_fps.get())
        except ValueError:
            target_fps = 5.0  # 默认帧率
            self.log_message("无效的帧率值，使用默认值5fps")
        
        # 计算帧间隔
        frame_interval = max(1, int(fps / target_fps)) 
        
        frames = []
        count = 0
        frame_data = []
        
        # 先收集所有需要处理的帧
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if count % frame_interval == 0:
                frame_data.append((count, frame))  # 保存帧索引和帧数据
            count += 1
            
        cap.release()
        
        if not frame_data:
            return
            
        # 使用多线程处理帧转换
        processed_frames = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            # 提交所有帧处理任务
            future_to_index = {executor.submit(self.process_frame, frame_info[0], frame_info[1]): frame_info[0] 
                             for frame_info in frame_data}
            
            # 收集处理结果
            for future in concurrent.futures.as_completed(future_to_index):
                try:
                    result = future.result()
                    if result is not None:
                        processed_frames.append(result)
                except Exception as e:
                    self.log_message(f"处理帧时出错: {str(e)}")
        
        # 按照原始帧顺序排序
        processed_frames.sort(key=lambda x: x[0])
        frames = [frame for _, frame in processed_frames]
        
        # 保存为GIF
        if frames:
            pil_frames = [Image.fromarray(frame) for frame in frames]
            
            # 计算每帧显示时间（毫秒）
            duration = int(1000 / target_fps)
            pil_frames[0].save(
                output_path,
                save_all=True,
                append_images=pil_frames[1:],
                duration=duration,
                loop=0
            )

    def process_frame(self, index, frame):
        """
        处理单个帧，调整大小并转换颜色格式
        返回 (index, processed_frame) 元组用于排序
        """
        try:
            # 获取用户设置的分辨率
            width_str = self.gif_width.get()
            height_str = self.gif_height.get()
            
            # 调整帧大小
            height, width = frame.shape[:2]
            
            # 根据用户设置调整尺寸
            if width_str.lower() != "原始" and width_str.isdigit():
                new_width = int(width_str)
                scale_factor = new_width / width
                new_height = int(height * scale_factor)
            elif height_str.lower() != "原始" and height_str.isdigit():
                new_height = int(height_str)
                scale_factor = new_height / height
                new_width = int(width * scale_factor)
            else:
                # 保持原始尺寸
                new_width = width
                new_height = height
                
            # 如果用户同时指定了宽高，则直接使用指定值
            if (width_str.lower() != "原始" and width_str.isdigit() and 
                height_str.lower() != "原始" and height_str.isdigit()):
                new_width = int(width_str)
                new_height = int(height_str)
            
            # 只有当尺寸改变时才调整大小
            if new_width != width or new_height != height:
                resized_frame = cv2.resize(frame, (new_width, new_height))
            else:
                resized_frame = frame
            
            # 转换颜色格式（OpenCV使用BGR，PIL使用RGB）
            rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            return (index, rgb_frame)
        except Exception as e:
            self.log_message(f"处理帧时出错: {str(e)}")
            return None

def main():
    root = tk.Tk()
    app = MediaConverter(root)
    root.mainloop()

if __name__ == "__main__":
    main()