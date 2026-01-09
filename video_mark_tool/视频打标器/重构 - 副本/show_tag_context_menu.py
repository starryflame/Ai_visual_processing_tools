# This is a method from class VideoTagger

import tkinter as tk

def show_tag_context_menu(self, event):
    """显示标记列表的右键菜单"""
    # 检查是否有选中的项目
    selection = self.tag_listbox.curselection()
    if selection:
        self.tag_listbox.selection_clear(0, tk.END)
        self.tag_listbox.selection_set(selection[0])
        self.tag_context_menu.post(event.x_root, event.y_root)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['show_tag_context_menu']
