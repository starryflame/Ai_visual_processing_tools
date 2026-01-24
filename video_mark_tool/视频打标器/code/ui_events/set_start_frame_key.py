# This is a method from class VideoTagger

import tkinter as tk

def set_start_frame_key(self, event=None):
    """通过键盘按键'a'设置开始帧"""
    # 检查焦点是否在输入控件上，如果是则不处理
    focused_widget = self.root.focus_get()
    if isinstance(focused_widget, (tk.Entry, tk.Text)):
        return "break"  # 不处理该事件
    if self.set_start_btn['state'] == 'normal':  # 只有按钮可用时才执行
        self.set_start_frame()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['set_start_frame_key']
