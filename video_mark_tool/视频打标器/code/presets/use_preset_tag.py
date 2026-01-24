# This is a method from class VideoTagger

import tkinter as tk

def use_preset_tag(self, preset_text):
    """使用预设标签，将其添加到标签输入框的开头"""
    current_text = self.tag_entry.get("1.0", tk.END).strip()
    if current_text:
        new_text = preset_text + "\n" + current_text
    else:
        new_text = preset_text
        
    self.tag_entry.delete("1.0", tk.END)
    self.tag_entry.insert("1.0", new_text)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['use_preset_tag']
