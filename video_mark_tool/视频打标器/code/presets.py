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
    # 启用删除按钮
    self.delete_preset_btn.config(state=tk.NORMAL)
    # 清空输入框
    self.preset_entry.delete(0, tk.END)


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
    
    # 绑定右键菜单事件
    preset_item.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "ai", index))
    thumbnail_label.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "ai", index))
    content_text.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "ai", index))


def use_preset_tag(self, preset_text):
    """使用预设标签，将其添加到标签输入框的开头"""
    current_text = self.tag_entry.get("1.0", tk.END).strip()
    if current_text:
        new_text = preset_text + "\n" + current_text
    else:
        new_text = preset_text
        
    self.tag_entry.delete("1.0", tk.END)
    self.tag_entry.insert("1.0", new_text)


def use_caption_preset(self):
    """使用选中的标签预设填充标签输入框"""


def edit_preset_tag(self):
    """编辑预设标签"""
    if hasattr(self, 'selected_preset_widget') and hasattr(self, 'selected_preset_type'):
        # 获取当前预设文本
        if self.selected_preset_type == "manual":
            current_text = self.manual_presets[self.selected_preset_index]
        else:  # AI 生成的预设
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
                    # 更新 AI 预设
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


def delete_preset_tag(self):
    """删除预设标签"""
    if hasattr(self, 'selected_preset_widget') and hasattr(self, 'selected_preset_type'):
        if messagebox.askyesno("确认删除", "确定要删除这个预设标签吗？", parent=self.root):
            if self.selected_preset_type == "manual":
                # 从手动预设列表中删除
                del self.manual_presets[self.selected_preset_index]
                # 重新创建所有手动预设项显示
                for widget in self.preset_scrollable_frame.winfo_children():
                    widget.destroy()
                
                # 重新创建所有预设项显示
                for i, preset in enumerate(self.manual_presets):
                    self.create_manual_preset_item(i, preset)
                
                # 重新创建 AI 预设项显示
                for i, preset in enumerate(self.caption_presets):
                    self.create_preset_item(i, preset["caption"], preset["image"])
            else:
                # 从 AI 预设列表中删除
                del self.caption_presets[self.selected_preset_index]
                # 重新创建所有预设项显示
                for widget in self.preset_scrollable_frame.winfo_children():
                    widget.destroy()
                
                # 重新创建所有手动预设项显示
                for i, preset in enumerate(self.manual_presets):
                    self.create_manual_preset_item(i, preset)
                
                # 重新创建 AI 预设项显示
                for i, preset in enumerate(self.caption_presets):
                    self.create_preset_item(i, preset["caption"], preset["image"])
            
            # 清除引用避免错误
            del self.selected_preset_widget
            del self.selected_preset_type
            del self.selected_preset_index


def delete_caption_preset(self):
    """清空所有标签预设"""
    if messagebox.askyesno("确认", "确定要删除所有标签预设吗？"):
        # 清空显示区域
        for widget in self.preset_scrollable_frame.winfo_children():
            widget.destroy()
        
        # 清空数据
        self.caption_presets.clear()


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


def apply_preset_to_all_tags(self):
    """将预设标签应用到所有已标记的视频片段标签开头"""
    if not hasattr(self, 'selected_preset_type'):
        return
        
    # 获取预设标签文本
    if self.selected_preset_type == "manual":
        preset_text = self.manual_presets[self.selected_preset_index]
    else:  # AI 生成的预设
        preset_text = self.caption_presets[self.selected_preset_index]["caption"]
        
    if not preset_text:
        messagebox.showerror("错误", "预设标签为空")
        return
        
    # 确认操作
    if not messagebox.askyesno("确认", f"确定要将预设标签 '{preset_text}' 添加到所有已标记片段的标签开头吗？", parent=self.root):
        return
        
    # 应用预设标签到所有标记
    updated_count = 0
    for i, tag in enumerate(self.tags):
        original_tag = tag["tag"]
        # 如果标签开头还没有这个预设标签，则添加
        if not original_tag.startswith(preset_text):
            new_tag = preset_text + "\n" + original_tag
            self.tags[i]["tag"] = new_tag
            # 更新列表框显示
            self.tag_listbox.delete(i)
            self.tag_listbox.insert(i, f"帧 {tag['start']}-{tag['end']}: {new_tag}")
            updated_count += 1
            
    messagebox.showinfo("完成", f"已将预设标签应用到 {updated_count} 个标记片段", parent=self.root)
    
    # 更新标记可视化
    self.draw_tag_markers()


__all__ = [
    'add_preset_tag',
    'create_manual_preset_item',
    'create_preset_item',
    'use_preset_tag',
    'use_caption_preset',
    'edit_preset_tag',
    'delete_preset_tag',
    'delete_caption_preset',
    'show_full_image',
    'apply_preset_to_all_tags'
]
