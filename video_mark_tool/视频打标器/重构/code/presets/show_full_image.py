# This is a method from class VideoTagger

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

def show_full_image(self, frame_image, caption, index):
    """显示完整的图像和标签"""
    # 创建新窗口显示完整图像
    image_window = tk.Toplevel(self.root)
    image_window.title("预设详情")
    image_window.geometry("900x1280")  # 增大默认窗口尺寸
    image_window.transient(self.root)
    
    # 将窗口居中
    image_window.update_idletasks()
    x = (image_window.winfo_screenwidth() // 2) - (900 // 2)
    y = (image_window.winfo_screenheight() // 2) - (700 // 2)
    image_window.geometry(f"900x700+{x}+{y}")
    
    # 图像显示
    image_frame = tk.Frame(image_window)
    image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 调整图像大小以适应显示区域
    image_obj = Image.fromarray(frame_image)
    image_obj.thumbnail((880, 400), Image.LANCZOS)
    photo = ImageTk.PhotoImage(image_obj)
    
    image_label = tk.Label(image_frame, image=photo)
    image_label.image = photo  # 保持引用
    image_label.pack()
    
    # 标签内容显示
    caption_frame = tk.Frame(image_window, height=200)  # 设置最大高度 300
    caption_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    caption_frame.pack_propagate(False)  # 阻止 Frame 自动调整大小

    tk.Label(caption_frame, text="标签内容:", font=self.font).pack(anchor=tk.W)
    
    # 创建带滚动条的文本框框架
    text_frame = tk.Frame(caption_frame)
    text_frame.pack(fill=tk.BOTH, expand=True)
    
    caption_text = tk.Text(text_frame, wrap=tk.WORD, font=self.font)
    caption_text.insert(tk.END, caption)
    
    # 配置文本框为可编辑状态
    caption_text.config(state=tk.NORMAL)
    
    # 添加滚动条并与文本框关联
    scrollbar = tk.Scrollbar(text_frame, command=caption_text.yview)
    caption_text.config(yscrollcommand=scrollbar.set)
    
    # 使用grid布局管理文本框和滚动条
    caption_text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    
    # 配置网格权重
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)
    
    # 按钮框架
    button_frame = tk.Frame(image_window)
    button_frame.pack(fill=tk.X, padx=10, pady=10)
    
    # 使用预设按钮
    def use_preset():
        self.tag_entry.delete("1.0", tk.END)
        self.tag_entry.insert("1.0", caption)
        image_window.destroy()
        
    tk.Button(button_frame, text="使用预设", command=use_preset, font=self.font).pack(side=tk.LEFT, padx=5)
    
    # 删除预设按钮
    def delete_preset():
        if messagebox.askyesno("确认", "确定要删除这个标签预设吗？", parent=image_window):
            # 从数据中删除
            del self.caption_presets[index]
            
            # 重新创建所有预设项显示
            for widget in self.preset_scrollable_frame.winfo_children():
                widget.destroy()
            
            # 修复：只重建AI预设项，不影响手动预设
            for i, preset in enumerate(self.manual_presets):
                self.create_manual_preset_item(i, preset)
                
            for i, preset in enumerate(self.caption_presets):
                self.create_preset_item(i, preset["caption"], preset["image"])
            
            image_window.destroy()
            
    tk.Button(button_frame, text="删除预设", command=delete_preset, font=self.font).pack(side=tk.LEFT, padx=5)
    
    # 添加:保存修改的函数
    def save_changes():
        # 获取文本框中的内容并更新预设
        updated_caption = caption_text.get("1.0", tk.END).strip()
        self.caption_presets[index]["caption"] = updated_caption
        
        # 更新预设列表中的显示
        for widget in self.preset_scrollable_frame.winfo_children():
            widget.destroy()
        
        # 重建所有预设项
        for i, preset in enumerate(self.manual_presets):
            self.create_manual_preset_item(i, preset)
            
        for i, preset in enumerate(self.caption_presets):
            self.create_preset_item(i, preset["caption"], preset["image"])
    
    # 在按钮框架中添加保存按钮
    tk.Button(button_frame, text="保存修改", command=save_changes, font=self.font).pack(side=tk.LEFT, padx=5)
    
    # 关闭按钮
    tk.Button(button_frame, text="关闭", command=image_window.destroy, font=self.font).pack(side=tk.RIGHT, padx=5)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['show_full_image']
