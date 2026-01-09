# This is a method from class VideoTagger
import tkinter as tk
from tkinter import messagebox

def edit_preset_tag(self):
    """编辑预设标签"""
    if hasattr(self, 'selected_preset_widget') and hasattr(self, 'selected_preset_type'):
        # 获取当前预设文本
        if self.selected_preset_type == "manual":
            current_text = self.manual_presets[self.selected_preset_index]
        else:  # AI生成的预设
            current_text = self.caption_presets[self.selected_preset_index]["caption"]
            
        # 创建编辑窗口
        edit_window = tk.Toplevel(self.root)
        edit_window.title("编辑预设标签")
        edit_window.geometry("300x150")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # 居中显示
        edit_window.update_idletasks()
        x = (edit_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (edit_window.winfo_screenheight() // 2) - (150 // 2)
        edit_window.geometry(f"300x150+{x}+{y}")
        
        tk.Label(edit_window, text="预设标签:", font=self.font).pack(pady=(20, 5))
        edit_entry = tk.Entry(edit_window, font=self.font, width=30)
        edit_entry.pack(pady=5, padx=20)
        edit_entry.insert(0, current_text)
        edit_entry.focus()
        
        def save_changes():
            new_text = edit_entry.get().strip()
            if new_text:
                if self.selected_preset_type == "manual":
                    # 更新手动预设
                    self.manual_presets[self.selected_preset_index] = new_text
                    # 更新显示文本
                    content_frame = self.selected_preset_widget.winfo_children()[0]  # 标签内容框架
                    content_text = content_frame.winfo_children()[0]  # 文本框
                    content_text.config(state=tk.NORMAL)
                    content_text.delete(1.0, tk.END)
                    content_text.insert(tk.END, new_text)
                    content_text.config(state=tk.DISABLED)
                else:
                    # 更新AI预设
                    self.caption_presets[self.selected_preset_index]["caption"] = new_text
                    # 更新显示文本
                    content_frame = self.selected_preset_widget.winfo_children()[1]  # 标签内容框架
                    content_text = content_frame.winfo_children()[0]  # 文本框
                    content_text.config(state=tk.NORMAL)
                    content_text.delete(1.0, tk.END)
                    content_text.insert(tk.END, new_text)
                    content_text.config(state=tk.DISABLED)
                edit_window.destroy()
            else:
                messagebox.showerror("错误", "预设标签不能为空", parent=edit_window)
        
        button_frame = tk.Frame(edit_window)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="保存", command=save_changes, font=self.font).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=edit_window.destroy, font=self.font).pack(side=tk.LEFT, padx=5)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['edit_preset_tag']
