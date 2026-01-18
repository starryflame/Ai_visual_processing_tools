# This is a method from class VideoTagger
import tkinter as tk


def add_preset_tag(self):
    """添加预设标签"""
    preset_text = self.preset_entry.get().strip()
    if not preset_text:
        return
        
    # 添加到手动预设列表
    self.manual_presets.append(preset_text)
    
    # 使用统一的方法创建预设项显示
    self.create_manual_preset_item(len(self.manual_presets) - 1, preset_text)
    # 启用删除按钮
    self.delete_preset_btn.config(state=tk.NORMAL)
    # 清空输入框
    self.preset_entry.delete(0, tk.END)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['add_preset_tag']
