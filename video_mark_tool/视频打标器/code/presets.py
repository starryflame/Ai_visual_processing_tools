# Preset Management Module - 标签预设管理模块
# 包含预设添加、编辑、删除和应用等功能

import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk


def add_preset_tag(self):
    """添加预设标签"""
    preset_text = self.preset_entry.get().strip()
    if not preset_text:
        return
        
    # 添加到手动预设列表
    self.manual_presets.append(preset_text)
    
    # 使用统一的方法创建预设项显示
    self.create_manual_preset_item(len(self.manual_presets) - 1, preset_text)
    # 清空输入框
    self.preset_entry.delete(0, tk.END)


def create_manual_preset_item(self, index, preset_text):
    """创建手动预设项显示 — 带图标、文本和操作按钮"""
    preset_item = tk.Frame(self.preset_scrollable_frame, bg="#f0f0f0", relief="raised", bd=1)
    preset_item.pack(fill=tk.X, padx=5, pady=5)

    # 图标框架（手动预设没有缩略图，用文字图标代替）
    icon_frame = tk.Frame(preset_item, bg="#f0f0f0", width=40)
    icon_frame.pack(side=tk.LEFT, padx=5, pady=5)
    icon_frame.pack_propagate(False)

    icon_label = tk.Label(icon_frame, text="【手动】", bg="#f0f0f0", font=("Microsoft YaHei", 8))
    icon_label.pack()

    # 标签内容框架
    content_frame = tk.Frame(preset_item, bg="#f0f0f0")
    content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    # 标签内容文本
    content_text = tk.Text(content_frame, wrap=tk.WORD, height=4, width=40, font=("Arial", 8))
    content_text.insert(tk.END, preset_text)
    content_text.config(state=tk.DISABLED)
    content_text.pack(fill=tk.BOTH, expand=True)

    # 点击打开预设详情窗口
    def on_click(event=None):
        self.show_manual_preset_window(preset_text, index)

    preset_item.bind("<Button-1>", on_click)
    icon_label.bind("<Button-1>", on_click)
    content_text.bind("<Button-1>", on_click)

    for child in preset_item.winfo_children():
        child.bind("<Button-1>", on_click)
        for subchild in child.winfo_children():
            subchild.bind("<Button-1>", on_click)


def show_manual_preset_window(self, preset_text, index):
    """打开手动预设详情窗口（可编辑、使用、删除）"""
    win = tk.Toplevel(self.root)
    win.title("预设详情")
    win.geometry("500x400")
    win.transient(self.root)
    win.grab_set()
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (500 // 2)
    y = (win.winfo_screenheight() // 2) - (400 // 2)
    win.geometry(f"500x400+{x}+{y}")

    tk.Label(win, text="预设标签:", font=self.font).pack(anchor=tk.W, padx=15, pady=(15, 5))

    text_frame = tk.Frame(win)
    text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

    caption_text = tk.Text(text_frame, wrap=tk.WORD, font=self.font, height=15)
    caption_text.insert(tk.END, preset_text)
    caption_text.config(state=tk.NORMAL)

    scrollbar = tk.Scrollbar(text_frame, command=caption_text.yview)
    caption_text.config(yscrollcommand=scrollbar.set)
    caption_text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)

    button_frame = tk.Frame(win)
    button_frame.pack(fill=tk.X, padx=15, pady=15)

    # 使用预设 — 直接生成标记片段
    def use_preset():
        new_text = caption_text.get("1.0", tk.END).strip()
        if not new_text:
            messagebox.showerror("错误", "标签内容为空", parent=win)
            return
        start = self.start_frame
        end = self.end_frame
        if start >= end:
            messagebox.showerror("错误", "请先设置开始帧和结束帧", parent=win)
            return
        self.tags.append({"start": start, "end": end, "tag": new_text})
        self.tag_listbox.insert(tk.END, f"帧 {start}-{end}: {new_text}")
        self.start_frame = 0
        self.end_frame = 0
        self.current_frame = end
        self.draw_tag_markers()
        self.show_frame()
        win.destroy()

    # 填入标签框
    def fill_tag_entry():
        new_text = caption_text.get("1.0", tk.END).strip()
        current = self.tag_entry.get("1.0", tk.END).strip()
        if current:
            self.tag_entry.delete("1.0", tk.END)
            self.tag_entry.insert("1.0", current + new_text)
        else:
            self.tag_entry.delete("1.0", tk.END)
            self.tag_entry.insert("1.0", new_text)
        win.destroy()

    tk.Button(button_frame, text="使用预设", command=use_preset, font=self.font).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="填入标签框", command=fill_tag_entry, font=self.font).pack(side=tk.LEFT, padx=5)


    # 保存修改
    def save_changes():
        new_text = caption_text.get("1.0", tk.END).strip()
        if not new_text:
            messagebox.showerror("错误", "标签不能为空", parent=win)
            return
        self.manual_presets[index] = new_text
        # 重建显示
        for w in self.preset_scrollable_frame.winfo_children():
            w.destroy()
        for i, p in enumerate(self.manual_presets):
            self.create_manual_preset_item(i, p)
        for i, p in enumerate(self.caption_presets):
            self.create_preset_item(i, p["caption"], p["image"])
        messagebox.showinfo("成功", "已保存修改", parent=win)

    tk.Button(button_frame, text="保存修改", command=save_changes, font=self.font).pack(side=tk.LEFT, padx=5)

    # 删除预设
    def delete_preset():
        if messagebox.askyesno("确认", "确定要删除这个预设吗？", parent=win):
            del self.manual_presets[index]
            for w in self.preset_scrollable_frame.winfo_children():
                w.destroy()
            for i, p in enumerate(self.manual_presets):
                self.create_manual_preset_item(i, p)
            for i, p in enumerate(self.caption_presets):
                self.create_preset_item(i, p["caption"], p["image"])
            win.destroy()

    tk.Button(button_frame, text="删除预设", command=delete_preset, font=self.font).pack(side=tk.LEFT, padx=5)

    tk.Button(button_frame, text="关闭", command=win.destroy, font=self.font).pack(side=tk.LEFT, padx=5)


def create_preset_item(self, index, caption, frame_image):
    """创建预设项显示"""
    # 创建预设项框架
    preset_item = tk.Frame(self.preset_scrollable_frame, bg="#f0f0f0", relief="raised", bd=1)
    preset_item.pack(fill=tk.X, padx=5, pady=5)
    
    # 缩略图框架
    thumbnail_frame = tk.Frame(preset_item, bg="#f0f0f0")
    thumbnail_frame.pack(side=tk.LEFT, padx=5, pady=5)
    
    # 创建缩略图
    thumbnail_image = Image.fromarray(frame_image)
    thumbnail_image = thumbnail_image.resize((60, 40), Image.LANCZOS)
    thumbnail_photo = ImageTk.PhotoImage(thumbnail_image)
    
    # 缩略图标签
    thumbnail_label = tk.Label(thumbnail_frame, image=thumbnail_photo, bg="#f0f0f0")
    thumbnail_label.image = thumbnail_photo  # 保持引用
    thumbnail_label.pack()
    
    # 标签内容框架
    content_frame = tk.Frame(preset_item, bg="#f0f0f0")
    content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # 标签内容文本
    content_text = tk.Text(content_frame, wrap=tk.WORD, height=4, width=40, font=("Arial", 8))
    content_text.insert(tk.END, caption)
    content_text.config(state=tk.DISABLED)
    content_text.pack(fill=tk.BOTH, expand=True)
    
    # 绑定点击事件
    def on_click(event=None):
        # 显示完整图像和标签
        self.show_full_image(frame_image, caption, index)
    
    preset_item.bind("<Button-1>", on_click)
    thumbnail_label.bind("<Button-1>", on_click)
    content_text.bind("<Button-1>", on_click)
    
    # 为所有子组件绑定点击事件
    for child in preset_item.winfo_children():
        child.bind("<Button-1>", on_click)
        for subchild in child.winfo_children():
            subchild.bind("<Button-1>", on_click)


def use_preset_tag(self, preset_text):
    """使用预设标签，将其添加到标签输入框的开头"""
    current_text = self.tag_entry.get("1.0", tk.END).strip()
    if current_text:
        new_text = preset_text + "\n" + current_text
    else:
        new_text = preset_text
        
    self.tag_entry.delete("1.0", tk.END)
    self.tag_entry.insert("1.0", new_text)


def delete_caption_preset(self):
    """清空所有标签预设"""
    if not self.caption_presets and not self.manual_presets:
        messagebox.showwarning("提示", "当前没有标签预设需要删除")
        return
    if messagebox.askyesno("确认", "确定要删除所有标签预设吗？"):
        for widget in self.preset_scrollable_frame.winfo_children():
            widget.destroy()
        self.caption_presets.clear()
        self.manual_presets.clear()


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
    
    # 视频播放区域
    video_frame = tk.Frame(image_window)
    video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 创建 Canvas 用于显示视频帧
    canvas = tk.Canvas(video_frame, width=880, height=400, bg='black')
    canvas.pack()

    # 播放控制变量
    is_playing = True
    current_frame_idx = self.start_frame
    
    # 添加一个引用存储当前播放任务 ID，以便后续取消
    play_task_id = None

    # 播放视频的函数（使用 after 方法）
    def play_video():
        nonlocal current_frame_idx, is_playing, play_task_id
        if not is_playing:
            return
            
        if current_frame_idx > self.end_frame:
            current_frame_idx = self.start_frame  # 循环回到开始
            
        # 获取当前帧
        frame = self.processed_frames[current_frame_idx]
        
        # 转换为 PIL 图像并调整大小
        image_obj = Image.fromarray(frame)
        image_obj.thumbnail((880, 400), Image.LANCZOS)
        
        # 转换为 PhotoImage 并在 Canvas 上显示
        photo = ImageTk.PhotoImage(image_obj)
        
        # 清除 Canvas 上的旧图像
        canvas.delete("all")
        canvas.create_image(880//2, 400//2, image=photo)
        canvas.image = photo  # 保持引用
        
        # 更新帧索引
        current_frame_idx += 1
        
        # 使用 after 方法安排下次更新，根据视频 FPS 调整播放速度
        play_task_id = canvas.after(int(1000 / self.fps), play_video)

    # 初始显示第一帧
    first_frame = self.processed_frames[self.start_frame]
    image_obj = Image.fromarray(first_frame)
    image_obj.thumbnail((880, 400), Image.LANCZOS)
    photo = ImageTk.PhotoImage(image_obj)
    canvas.create_image(880//2, 400//2, image=photo)
    canvas.image = photo
    
    # 启动播放
    play_video()

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
    
    # 使用 grid 布局管理文本框和滚动条
    caption_text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    
    # 配置网格权重
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)
    
    # 按钮框架
    button_frame = tk.Frame(image_window)
    button_frame.pack(fill=tk.X, padx=10, pady=10)
    
    # 使用预设按钮 — 直接生成标记片段
    def use_preset():
        start = self.start_frame
        end = self.end_frame
        if start >= end:
            messagebox.showerror("错误", "请先设置开始帧和结束帧", parent=image_window)
            return
        if not caption.strip():
            messagebox.showerror("错误", "标签内容为空", parent=image_window)
            return
        self.tags.append({"start": start, "end": end, "tag": caption})
        self.tag_listbox.insert(tk.END, f"帧 {start}-{end}: {caption}")
        self.start_frame = 0
        self.end_frame = 0
        self.current_frame = end
        self.draw_tag_markers()
        self.show_frame()
        image_window.destroy()
        
    tk.Button(button_frame, text="使用预设", command=use_preset, font=self.font).pack(side=tk.LEFT, padx=5)

    # 填入标签框 — 把内容追加到标签输入框
    def fill_tag_entry():
        current = self.tag_entry.get("1.0", tk.END).strip()
        if current:
            self.tag_entry.delete("1.0", tk.END)
            self.tag_entry.insert("1.0", current + caption)
        else:
            self.tag_entry.delete("1.0", tk.END)
            self.tag_entry.insert("1.0", caption)
        image_window.destroy()

    tk.Button(button_frame, text="填入标签框", command=fill_tag_entry, font=self.font).pack(side=tk.LEFT, padx=5)

    # 删除预设按钮
    def delete_preset():
        if messagebox.askyesno("确认", "确定要删除这个标签预设吗？", parent=image_window):
            # 从数据中删除
            del self.caption_presets[index]
            
            # 重新创建所有预设项显示
            for widget in self.preset_scrollable_frame.winfo_children():
                widget.destroy()
            
            # 修复：只重建 AI 预设项，不影响手动预设
            for i, preset in enumerate(self.manual_presets):
                self.create_manual_preset_item(i, preset)
                
            for i, preset in enumerate(self.caption_presets):
                self.create_preset_item(i, preset["caption"], preset["image"])
            
            image_window.destroy()
            
    tk.Button(button_frame, text="删除预设", command=delete_preset, font=self.font).pack(side=tk.LEFT, padx=5)
    
    # 添加：保存修改的函数
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
    
    # 当窗口关闭时停止播放
    def on_closing():
        nonlocal is_playing
        is_playing = False
        # 如果存在播放任务，则取消它
        if play_task_id is not None:
            canvas.after_cancel(play_task_id)
        image_window.destroy()
    
    image_window.protocol("WM_DELETE_WINDOW", on_closing)


__all__ = [
    'add_preset_tag',
    'create_manual_preset_item',
    'show_manual_preset_window',
    'create_preset_item',
    'use_preset_tag',
    'delete_caption_preset',
    'show_full_image'
]
