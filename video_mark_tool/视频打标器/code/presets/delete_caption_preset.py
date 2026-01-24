# This is a method from class VideoTagger
from tkinter import messagebox

def delete_caption_preset(self):
    """清空所有标签预设"""
    if messagebox.askyesno("确认", "确定要删除所有标签预设吗？"):
        # 清空显示区域
        for widget in self.preset_scrollable_frame.winfo_children():
            widget.destroy()
        
        # 清空数据
        self.caption_presets.clear()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['delete_caption_preset']
