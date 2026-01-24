# This is a method from class VideoTagger

def decrease_font(self):
    """减小字体"""
    if self.font_size > 1:
        self.font_size -= 1
        self.update_font()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['decrease_font']
