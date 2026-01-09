# This is a method from class VideoTagger

def on_window_resize(self, event):
    """处理窗口大小变化事件"""
    if event.widget == self.root:  # 只处理主窗口的大小变化
        # 重新绘制标记可视化
        self.draw_tag_markers()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['on_window_resize']
