# This is a method from class VideoTagger

import tkinter as tk

def toggle_play_with_key(self, event=None):
    """通过键盘空格键切换播放状态"""
    # 检查焦点是否在输入控件上，如果是则不处理
    focused_widget = self.root.focus_get()
    if isinstance(focused_widget, (tk.Entry, tk.Text)):
        return "break"  # 不处理该事件
    self.toggle_play()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['toggle_play_with_key']
