# This is a method from class VideoTagger

import cv2
import tkinter as tk
from tkinter import ttk

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
            
            # 将视频帧调整为720p以提高性能
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
    self.auto_load_tag_records()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['preprocess_frames']
