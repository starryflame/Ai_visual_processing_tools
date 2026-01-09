# This is a method from class VideoTagger


def on_progress_change(self, value):
    if not self.frames_loaded:
        return
        
    new_frame = int(float(value))
    
    # 如果已经设置了开始帧，限制不能拖动到开始帧之前
    if self.start_frame > 0 and new_frame < self.start_frame:
        self.current_frame = self.start_frame
        self.progress.set(self.start_frame)
    else:
        self.current_frame = new_frame
        
    self.show_frame()
    self.draw_tag_markers()
    self.highlight_tag_for_current_frame()  # 添加这一行来高亮当前帧对应的标签

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['on_progress_change']
