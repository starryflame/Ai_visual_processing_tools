# This is a method from class VideoTagger
import cv2
import tkinter as tk
from tkinter import filedialog
import os

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
    
    # 执行与原始load_video相同的操作
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
    
    # 更新UI状态
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
    self.ai_generate_btn.config(state=tk.NORMAL)  # 启用AI生成按钮
    
    # 预处理所有帧
    self.preprocess_frames()
    
    # 刷新列表以高亮当前视频
    self.refresh_video_list()
    
    # 关闭视频管理窗口
    self.video_manager_window.destroy()

def load_video(self):
    """修改原load_video函数，改为打开视频管理器"""
    self.load_video_manager()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['load_video', 'load_video_manager', 'add_single_video', 'add_video_folder', 'refresh_video_list', 'load_selected_video']