# This is a method from class VideoTagger

import tkinter as tk

def update_widget_font(self, widget):
    """递归更新控件字体"""
    try:
        if isinstance(widget, (tk.Label, tk.Button, tk.Entry)):
            widget.config(font=self.font)
    except:
        pass
        
    for child in widget.winfo_children():
        self.update_widget_font(child)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['update_widget_font']
