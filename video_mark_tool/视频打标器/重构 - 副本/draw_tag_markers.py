# This is a method from class VideoTagger

def draw_tag_markers(self):
    """在进度条上绘制标记段的可视化"""
    self.progress_canvas.delete("all")
    
    if self.total_frames <= 0:
        return
        
    canvas_width = self.progress_canvas.winfo_width()
    if canvas_width <= 1:  # 初始时可能为1
        canvas_width = self.progress.winfo_width()
        
    # 绘制整个时间轴
    self.progress_canvas.create_rectangle(0, 10, canvas_width, 20, fill="#ddd", outline="")
    
    # 定义多种颜色用于不同标记
    colors = ["blue", "red", "green", "orange", "purple", "brown", "pink", "gray", "olive", "cyan"]
    
    # 绘制每个标记段
    for i, tag in enumerate(self.tags):
        # 确保标记位置不会完全位于边缘之外
        start_x = max(2, int((tag["start"] / self.total_frames) * canvas_width))
        end_x = min(canvas_width-2, int((tag["end"] / self.total_frames) * canvas_width))
        # 使用不同颜色并添加透明效果（通过宽度和轮廓实现视觉上的区分）
        color = colors[i % len(colors)]
        # 绘制半透明效果的标记
        self.progress_canvas.create_rectangle(start_x, 10, end_x, 20, fill=color, outline=color, stipple="gray50")
        # 在标记上显示序号
        if end_x - start_x > 20:  # 只有当标记足够宽时才显示文字
            self.progress_canvas.create_text((start_x + end_x) // 2, 15, text=str(i+1), fill="white", font=("Arial", 8))
            
    # 绘制排除片段（用红色显示）
    for segment in self.excluded_segments:
        start_x = max(2, int((segment["start"] / self.total_frames) * canvas_width))
        end_x = min(canvas_width-2, int((segment["end"] / self.total_frames) * canvas_width))
        self.progress_canvas.create_rectangle(start_x, 10, end_x, 20, fill="red", outline="red", stipple="gray25")

    # 绘制当前帧位置指示器 (确保在可视区域内)
    current_x = max(1, min(canvas_width-1, int((self.current_frame / self.total_frames) * canvas_width)))
    self.progress_canvas.create_line(current_x, 0, current_x, 30, fill="red", width=2)
    
    # 绘制开始帧和结束帧标记 (确保在可视区域内)
    if self.start_frame > 0:
        start_x = max(1, min(canvas_width-1, int((self.start_frame / self.total_frames) * canvas_width)))
        self.progress_canvas.create_line(start_x, 5, start_x, 25, fill="green", width=2)
        # 调整文本位置避免被遮挡
        text_x = start_x
        if start_x < 30:  # 如果太靠近左边
            text_x = start_x + 25
            anchor = "w"
        elif start_x > canvas_width - 30:  # 如果太靠近右边
            text_x = start_x - 25
            anchor = "e"
        else:
            anchor = "n"
        self.progress_canvas.create_text(text_x, 5, text=f"开始:{self.start_frame}", anchor=anchor, fill="green", font=("Arial", 8))
        
    if self.end_frame > 0:
        end_x = max(1, min(canvas_width-1, int((self.end_frame / self.total_frames) * canvas_width)))
        self.progress_canvas.create_line(end_x, 5, end_x, 25, fill="purple", width=2)
        # 调整文本位置避免被遮挡
        text_x = end_x
        if end_x < 30:  # 如果太靠近左边
            text_x = end_x + 25
            anchor = "w"
        elif end_x > canvas_width - 30:  # 如果太靠近右边
            text_x = end_x - 25
            anchor = "e"
        else:
            anchor = "n"
        self.progress_canvas.create_text(text_x, 25, text=f"结束:{self.end_frame}", anchor=anchor, fill="purple", font=("Arial", 8))
        
    # 绘制时间轴上的时间标记
    if self.fps > 0:
        # 绘制开始时间
        self.progress_canvas.create_text(5, 35, text="0s", anchor="w", fill="black", font=("Arial", 8))
        
        # 绘制结束时间
        total_time = self.total_frames / self.fps
        self.progress_canvas.create_text(canvas_width-5, 35, text=f"{total_time:.1f}s", anchor="e", fill="black", font=("Arial", 8))
        
        # 如果有开始帧，显示当前选择段的时间长度
        if self.start_frame > 0 and self.current_frame >= self.start_frame:
            selected_time = (self.current_frame - self.start_frame) / self.fps
            mid_x = int(((self.start_frame + self.current_frame) / 2 / self.total_frames) * canvas_width)
            # 确保文本在可视范围内
            mid_x = max(20, min(canvas_width-20, mid_x))
            self.progress_canvas.create_text(mid_x, 45, text=f"{selected_time:.2f}s", fill="blue", font=("Arial", 8))

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['draw_tag_markers']
