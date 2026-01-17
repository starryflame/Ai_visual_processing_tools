# This is a method from class VideoTagger
import tkinter as tk


def highlight_tag_for_current_frame(self):
    """高亮显示当前帧对应的标签行"""
    # 清除之前的高亮
    self.tag_listbox.selection_clear(0, tk.END)
    
    # 查找当前帧所在的标记区间
    for i, tag in enumerate(self.tags):
        if tag["start"] <= self.current_frame <= tag["end"]:
            # 高亮对应的标签行
            self.tag_listbox.selection_set(i)
            # 确保该项在可视区域内
            self.tag_listbox.see(i)
            break

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['highlight_tag_for_current_frame']
