# This is a method from class VideoTagger
import cv2
import tkinter as tk
from tkinter import filedialog
def load_video(self):
    file_path = filedialog.askopenfilename(
        title="选择视频文件",
        filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv")]
    )
    
    if not file_path:
        return
        
    self.video_path = file_path
    
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

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['load_video']
