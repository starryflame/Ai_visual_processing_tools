# This is a method from class VideoTagger

def clear_frame_marks(self):
    """清空开始帧和结束帧的标记"""
    self.start_frame = 0
    self.end_frame = 0
    self.draw_tag_markers()  # 更新标记可视化

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['clear_frame_marks']
