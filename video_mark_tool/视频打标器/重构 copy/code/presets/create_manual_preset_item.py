# This is a method from class VideoTagger
import tkinter as tk


def create_manual_preset_item(self, index, preset_text):
    """创建手动预设项显示"""
    # 创建预设项框架
    preset_item = tk.Frame(self.preset_scrollable_frame, bg="#f0f0f0", relief="raised", bd=1)
    preset_item.pack(fill=tk.X, padx=5, pady=5)
    
    # 标签内容框架
    content_frame = tk.Frame(preset_item, bg="#f0f0f0")
    content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # 标签内容文本
    content_text = tk.Text(content_frame, wrap=tk.WORD, height=4, width=20, font=("Arial", 8))
    content_text.insert(tk.END, preset_text)
    content_text.config(state=tk.DISABLED)
    content_text.pack(fill=tk.BOTH, expand=True)
    
    # 绑定点击事件，用于使用预设
    def on_click(event=None):
        self.use_preset_tag(preset_text)
    
    preset_item.bind("<Button-1>", on_click)
    content_text.bind("<Button-1>", on_click)
    
    # 为所有子组件绑定点击事件
    for child in preset_item.winfo_children():
        child.bind("<Button-1>", on_click)
        for subchild in child.winfo_children():
            subchild.bind("<Button-1>", on_click)
    
    # 绑定右键菜单事件
    preset_item.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "manual", index))
    content_text.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "manual", index))

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['create_manual_preset_item']
