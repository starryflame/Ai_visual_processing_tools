# This is a method from class VideoTagger

import tkinter as tk
from PIL import Image, ImageTk

def show_frame(self):
    if not self.frames_loaded or not self.processed_frames:
        return
        
    if self.current_frame < len(self.processed_frames):
        frame = self.processed_frames[self.current_frame]
        
        # 转换为PIL Image
        image = Image.fromarray(frame)
        
        # 获取画布尺寸
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        # 如果画布尺寸为1（初始状态），使用默认尺寸
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
        
        # 转换为PhotoImage
        photo = ImageTk.PhotoImage(resized_image)
        
        # 清除画布并显示新图像
        self.video_canvas.delete("all")
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        self.video_canvas.create_image(x, y, anchor=tk.NW, image=photo)
        self.video_canvas.image = photo  # 保持引用
        
        # 更新进度条和帧数显示
        self.progress.set(self.current_frame)
        self.frame_label.config(text=f"帧: {self.current_frame}/{self.total_frames-1}")

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['show_frame']
