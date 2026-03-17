# Video Processing Module - 视频处理模块
# 包含视频加载、播放、帧处理和保存等功能

import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk


def load_video_manager(self):
    """创建视频管理窗口，用于添加和显示视频"""
    # 创建视频管理窗口
    self.video_manager_window = tk.Toplevel(self.root)
    self.video_manager_window.title("视频管理")
    self.video_manager_window.geometry("800x600")
    
    # 设置窗口属性，使其始终在最前面
    self.video_manager_window.transient(self.root)  # 设置为临时窗口，依附于主窗口
    self.video_manager_window.grab_set()  # 模态化窗口，独占焦点
    
    # 视频列表存储
    if not hasattr(self, 'video_list'):
        self.video_list = []
    
    # 创建添加按钮和列表框架
    top_frame = tk.Frame(self.video_manager_window)
    top_frame.pack(pady=10, fill=tk.X)
    
    # 添加新视频按钮
    add_video_btn = tk.Button(top_frame, text="添加视频文件", command=self.add_single_video)
    add_video_btn.pack(side=tk.LEFT, padx=5)
    
    add_folder_btn = tk.Button(top_frame, text="添加视频文件夹", command=self.add_video_folder)
    add_folder_btn.pack(side=tk.LEFT, padx=5)
    
    # 加载选中的视频
    load_selected_btn = tk.Button(top_frame, text="加载选中视频", command=self.load_selected_video)
    load_selected_btn.pack(side=tk.RIGHT, padx=5)
    
    # 创建视频列表框
    list_frame = tk.Frame(self.video_manager_window)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 滚动条
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # 视频列表
    self.video_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
    self.video_listbox.pack(fill=tk.BOTH, expand=True)
    
    scrollbar.config(command=self.video_listbox.yview)
    
    # 绑定双击事件 - 双击直接加载视频
    self.video_listbox.bind('<Double-Button-1>', lambda event: self.load_selected_video())
    
    # 刷新视频列表显示
    self.refresh_video_list()


def add_single_video(self):
    """添加单个视频文件"""
    file_path = filedialog.askopenfilename(
        title="选择视频文件",
        filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv")]
    )
    
    if file_path and file_path not in self.video_list:
        self.video_list.append(file_path)
        self.refresh_video_list()


def add_video_folder(self):
    """添加包含视频的文件夹"""
    folder_path = filedialog.askdirectory(title="选择包含视频的文件夹")
    
    if not folder_path:
        return
        
    video_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(video_extensions):
                full_path = os.path.join(root, file)
                if full_path not in self.video_list:
                    self.video_list.append(full_path)
    
    self.refresh_video_list()


def refresh_video_list(self):
    """刷新视频列表显示"""
    self.video_listbox.delete(0, tk.END)
    current_loaded_index = -1  # 记录当前加载视频的索引
    
    for i, video_path in enumerate(self.video_list):
        filename = os.path.basename(video_path)
        self.video_listbox.insert(tk.END, f"{filename}")
        
        # 如果这个视频是当前加载的视频，则高亮显示
        if hasattr(self, 'video_path') and video_path == self.video_path:
            self.video_listbox.itemconfig(i, {'bg': 'lightblue'})
            current_loaded_index = i  # 记录当前加载视频的索引
    
    # 如果找到了当前加载的视频，则自动滚动到该位置
    if current_loaded_index >= 0:
        self.video_listbox.see(current_loaded_index)


def load_selected_video(self):
    """加载选中的视频"""
    selected_index = self.video_listbox.curselection()
    if not selected_index:
        return
    
    # 获取完整路径（去除显示的路径信息）
    video_path = self.video_list[selected_index[0]]
    
    # 执行与原始 load_video 相同的操作
    self.video_path = video_path
    
    # 释放之前的视频捕获对象
    if self.cap:
        self.cap.release()
        
    self.cap = cv2.VideoCapture(self.video_path)
    self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    self.fps = self.cap.get(cv2.CAP_PROP_FPS)
    self.current_frame = 0
    
    # 清空之前处理的帧
    self.processed_frames = []
    self.frames_loaded = False
    self.tags = []  # 清空标记
    self.excluded_segments = []  # 清空排除片段
    self.tag_listbox.delete(0, tk.END)  # 清空列表框
    self.export_btn.config(state=tk.DISABLED)  # 禁用导出按钮
    self.save_record_btn.config(state=tk.DISABLED)  # 禁用保存记录按钮
    self.load_record_btn.config(state=tk.DISABLED)  # 禁用加载记录按钮
    
    # 更新 UI 状态
    self.progress.config(to=self.total_frames-1, state=tk.NORMAL)
    self.play_btn.config(state=tk.NORMAL)
    self.prev_frame_btn.config(state=tk.NORMAL)
    self.next_frame_btn.config(state=tk.NORMAL)
    self.set_start_btn.config(state=tk.NORMAL)
    self.set_end_btn.config(state=tk.NORMAL)
    self.clear_frames_btn.config(state=tk.NORMAL)  # 确保启用清空按钮
    self.add_tag_btn.config(state=tk.NORMAL)
    self.exclude_segment_btn.config(state=tk.NORMAL)  # 启用排除片段按钮
    self.auto_segment_btn.config(state=tk.NORMAL)  # 启用自动分段按钮
    self.ai_generate_btn.config(state=tk.NORMAL)  # 启用 AI 生成按钮
    
    # 预处理所有帧
    self.preprocess_frames()
    
    # 刷新列表以高亮当前视频
    self.refresh_video_list()
    
    # 关闭视频管理窗口
    self.video_manager_window.destroy()


def load_video(self):
    """修改原 load_video 函数，改为打开视频管理器"""
    self.load_video_manager()


def show_frame(self):
    if not self.frames_loaded or not self.processed_frames:
        return
        
    if self.current_frame < len(self.processed_frames):
        frame = self.processed_frames[self.current_frame]
        
        # 转换为 PIL Image
        image = Image.fromarray(frame)
        
        # 获取画布尺寸
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        # 如果画布尺寸为 1（初始状态），使用默认尺寸
        if canvas_width <= 1:
            canvas_width = 800
        if canvas_height <= 1:
            canvas_height = 600
        
        # 计算缩放比例，确保整个图像都能显示在画布内
        img_width, img_height = image.size
        scale_width = canvas_width / img_width
        scale_height = canvas_height / img_height
        scale = min(scale_width, scale_height)
        
        # 如果图像比画布小，则不放大
        if scale > 1:
            scale = 1
        
        # 计算新尺寸
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        
        # 调整图像大小
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # 转换为 PhotoImage
        photo = ImageTk.PhotoImage(resized_image)
        
        # 清除画布并显示新图像
        self.video_canvas.delete("all")
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        self.video_canvas.create_image(x, y, anchor=tk.NW, image=photo)
        self.video_canvas.image = photo  # 保持引用
        
        # 更新进度条和帧数显示
        self.progress.set(self.current_frame)
        self.frame_label.config(text=f"帧：{self.current_frame}/{self.total_frames-1}")


def play_video(self):
    if not self.playing or not self.frames_loaded:
        return
        
    self.current_frame += 1
    if self.current_frame >= self.total_frames:
        self.current_frame = 0
        
    self.show_frame()
    self.draw_tag_markers()
    self.root.after(int(1000/self.fps), self.play_video)


def preprocess_frames(self):
    """预处理所有视频帧并存储为图片"""
    if not self.cap:
        return
        
    # 显示加载提示和进度条
    self.loading_window = tk.Toplevel(self.root)
    self.loading_window.title("加载中")
    self.loading_window.geometry("300x200")
    self.loading_window.transient(self.root)
    self.loading_window.grab_set()  # 模态窗口
    
    # 将窗口居中显示
    self.loading_window.update_idletasks()
    x = (self.loading_window.winfo_screenwidth() // 2) - (300 // 2)
    y = (self.loading_window.winfo_screenheight() // 2) - (100 // 2)
    self.loading_window.geometry(f"300x150+{x}+{y}")
    
    tk.Label(self.loading_window, text="正在预处理视频帧，请稍候...", font=self.font).pack(pady=10)
    
    # 创建进度条
    self.loading_progress = ttk.Progressbar(self.loading_window, mode='determinate', length=200)
    self.loading_progress.pack(pady=10)
    self.loading_progress['maximum'] = self.total_frames
    
    # 显示进度百分比的标签
    self.loading_label = tk.Label(self.loading_window, text="0%", font=self.font)
    self.loading_label.pack()
    
    self.root.update()
    
    # 重新打开视频文件以确保从头开始
    self.cap.release()
    self.cap = cv2.VideoCapture(self.video_path)
    
    # 从配置文件读取目标帧率
    target_fps = self.config.getint('PROCESSING', 'target_frame_rate', fallback=24)
    
    # 计算帧采样间隔
    if self.fps > target_fps:
        frame_interval = self.fps / target_fps
        effective_fps = target_fps
    else:
        frame_interval = 1
        effective_fps = self.fps
        
    # 处理每一帧
    processed_frame_count = 0
    i = 0
    while True:
        ret, frame = self.cap.read()
        if not ret:
            break
            
        # 检查是否应该保留这一帧
        if i % frame_interval < 1:
            # 转换颜色格式
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 将视频帧调整为 720p 以提高性能
            frame = self.resize_to_720p(frame)
            
            # 存储处理后的帧
            self.processed_frames.append(frame)
            processed_frame_count += 1
            
            # 更新进度条
            self.loading_progress['value'] = i + 1
            progress_percent = int((i + 1) / self.total_frames * 100)
            self.loading_label.config(text=f"{progress_percent}%")
            self.loading_window.update()
            
        i += 1
            
    self.frames_loaded = True
    # 更新总帧数和帧率为处理后的值
    self.total_frames = processed_frame_count
    self.fps = effective_fps
    
    # 关闭加载窗口
    self.loading_window.destroy()
    
    # 更新进度条范围以匹配处理后的帧数
    self.progress.config(to=self.total_frames-1)
    
    # 更新导出帧率选项为处理后的帧率
    self.export_fps.set(f"{self.fps:.2f}")
    
    # 启用保存和加载记录按钮
    self.save_record_btn.config(state=tk.NORMAL)
    self.load_record_btn.config(state=tk.NORMAL)
            
    # 显示第一帧
    self.show_frame()
    self.draw_tag_markers()  # 绘制标记可视化
    
    # 尝试自动加载该视频的标记记录
    #self.auto_load_tag_records()


def resize_to_720p(self, frame):
    """
    将帧调整为 720p 分辨率以提高性能
    """
    # 从配置文件读取目标高度
    target_height = self.config.getint('PROCESSING', 'target_frame_height', fallback=720)
    
    h, w = frame.shape[:2]
    
    # 如果高度已经小于等于 target_height，则不调整
    if h <= target_height:
        return frame
        
    # 计算新尺寸保持宽高比
    new_height = target_height
    new_width = int(w * (new_height / h))
    
    # 调整帧大小
    resized_frame = cv2.resize(frame, (new_width, new_height))
    return resized_frame


def save_and_replace_video(app):
    """保存起始帧到末尾帧区间为新视频，替换原视频"""
    if not app.video_path:
        messagebox.showwarning("警告", "请先加载视频！")
        return
    
    if app.start_frame >= app.end_frame:
        messagebox.showwarning("警告", "请先设置有效的起始帧和结束帧（起始帧 < 结束帧）！")
        return
    
    # 确认操作
    confirm = messagebox.askyesno("确认", 
        f"将保存第 {app.start_frame} 帧到第 {app.end_frame} 帧的视频片段\n"
        f"并替换原视频文件：{os.path.basename(app.video_path)}\n\n"
        f"此操作不可逆，是否继续？")
    
    if not confirm:
        return
    
    try:
        # 获取导出帧率
        fps_str = app.export_fps.get()
        if fps_str == "原始帧率" or fps_str == "":
            output_fps = app.fps
        else:
            output_fps = float(fps_str)
        
        # 获取视频目录和文件名
        video_dir = os.path.dirname(app.video_path)
        video_name = os.path.basename(app.video_path)
        
        # 创建临时文件名
        temp_path = os.path.join(video_dir, f"_temp_{video_name}")
        
        # 打开视频进行读取
        cap = cv2.VideoCapture(app.video_path)
        if not cap.isOpened():
            messagebox.showerror("错误", "无法打开视频文件！")
            return
        
        # 获取视频属性
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, output_fps, (frame_width, frame_height))
        
        if not out.isOpened():
            messagebox.showerror("错误", "无法创建输出视频文件！")
            cap.release()
            return
        
        # 读取并写入指定帧区间
        cap.set(cv2.CAP_PROP_POS_FRAMES, app.start_frame)
        frames_written = 0
        total_frames = app.end_frame - app.start_frame
        
        progress_window = tk.Toplevel(app.root)
        progress_window.title("保存视频中...")
        progress_window.geometry("300x100")
        progress_window.transient(app.root)
        progress_window.grab_set()
        
        progress_label = tk.Label(progress_window, text=f"进度：0/{total_frames}", font=app.font)
        progress_label.pack(pady=10)
        progress_bar = ttk.Progressbar(progress_window, length=250, mode='determinate')
        progress_bar.pack(pady=5)
        progress_bar["maximum"] = total_frames
        
        app.root.update()
        
        while True:
            ret, frame = cap.read()
            if not ret or cap.get(cv2.CAP_PROP_POS_FRAMES) > app.end_frame:
                break
            
            out.write(frame)
            frames_written += 1
            
            # 更新进度
            progress_label.config(text=f"进度：{frames_written}/{total_frames}")
            progress_bar["value"] = frames_written
            if frames_written % 10 == 0:
                app.root.update()
        
        cap.release()
        out.release()
        
        progress_window.destroy()
        
        if frames_written == 0:
            messagebox.showerror("错误", "未能写入任何帧！")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return
        
        # 关闭当前视频
        if app.cap:
            app.cap.release()
            app.cap = None
        
        # 删除原文件，重命名临时文件
        os.remove(app.video_path)
        os.rename(temp_path, app.video_path)
        
        messagebox.showinfo("成功", f"视频已保存并替换！\n共保存 {frames_written} 帧")
        
    except Exception as e:
        messagebox.showerror("错误", f"保存视频时出错：{str(e)}")
        # 清理临时文件
        temp_path = os.path.join(os.path.dirname(app.video_path), f"_temp_{os.path.basename(app.video_path)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)


__all__ = [
    'load_video', 
    'load_video_manager', 
    'add_single_video', 
    'add_video_folder', 
    'refresh_video_list', 
    'load_selected_video',
    'show_frame',
    'play_video',
    'preprocess_frames',
    'resize_to_720p',
    'save_and_replace_video'
]
