# This is a method from class VideoTagger


def set_end_frame(self):
    self.end_frame = self.current_frame
    self.draw_tag_markers()  # 更新标记可视化

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['set_end_frame']
