#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双面板图片配对工具 - GUI 版本
使用方法：直接运行，通过图形界面选择文件夹，左右面板分别管理图片，支持导出配对
支持深色模式和拖拽文件夹导入
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from pathlib import Path
import shutil
from PIL import Image, ImageTk
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入 tkinterdnd2 以支持拖拽功能
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# 深色模式配色方案
DARK_BG = "#2b2b2b"
DARK_FG = "#ffffff"
DARK_ENTRY_BG = "#3c3c3c"
DARK_BUTTON_BG = "#4a4a4a"
DARK_BUTTON_FG = "#ffffff"
DARK_CONTAINER_BG = "#1e1e1e"
DARK_HIGHLIGHT = "#0078d4"


class ImagePanel:
    """单侧图片面板"""
    
    def __init__(self, parent, name, side, main_window, dark_mode=True):
        self.parent = parent
        self.name = name
        self.side = side
        self.main_window = main_window
        self.dark_mode = dark_mode
        self.folder_path = tk.StringVar()
        self.image_files = []
        self.current_index = 0
        self.current_image = None
        self.paired_images = set()  # 记录已配对的图片文件名
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建面板组件"""
        # 面板框架
        if self.dark_mode:
            frame = tk.LabelFrame(self.parent, text=self.name, padx=10, pady=10, 
                                  bg=DARK_BG, fg=DARK_FG)
        else:
            frame = tk.LabelFrame(self.parent, text=self.name, padx=10, pady=10)
        frame.pack(side=self.side, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 文件夹选择
        folder_frame = tk.Frame(frame, bg=DARK_BG if self.dark_mode else None)
        folder_frame.pack(fill=tk.X, pady=5)
        tk.Label(folder_frame, text="文件夹:", width=8, 
                 bg=DARK_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT)
        tk.Entry(folder_frame, textvariable=self.folder_path, width=25,
                 bg=DARK_ENTRY_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=5)
        tk.Button(folder_frame, text="浏览", command=self.select_folder, width=8,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT)
        tk.Button(folder_frame, text="刷新", command=self.refresh_images, width=8,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=5)
        
        # 图片展示框 - 使用独立容器框起来，防止被变化
        image_container = tk.Frame(frame, relief=tk.SUNKEN, borderwidth=2, 
                                   bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0")
        image_container.pack(fill=tk.BOTH, expand=False, pady=10, padx=5)
        # 禁止容器根据子组件自动调整大小，防止被挤压
        image_container.pack_propagate(False)
        # 设置固定高度，确保图片展示区域不会被压缩
        image_container.config(height=800)
        
        # 添加拖拽功能提示标签
        if self.dark_mode:
            drop_hint = tk.Label(image_container, text="可拖拽文件夹到此处", 
                                bg=DARK_CONTAINER_BG, fg="#888888")
            drop_hint.pack(side=tk.BOTTOM, pady=5)
        
        self.image_label = tk.Label(image_container, text="暂无图片", 
                                    bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0",
                                    fg=DARK_FG if self.dark_mode else None,
                                    width=80, height=50)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # 绑定拖拽事件（如果支持）
        if DND_AVAILABLE and self.dark_mode:
            self.bind_drag_drop(image_container)
        
        # 图片列表
        list_frame = tk.Frame(frame, bg=DARK_BG if self.dark_mode else None)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        tk.Label(list_frame, text="图片列表:",
                 bg=DARK_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(anchor=tk.W)
        list_frame.config(height=100)
        self.listbox = tk.Listbox(list_frame, height=5,
                                  bg=DARK_ENTRY_BG if self.dark_mode else None,
                                  fg=DARK_FG if self.dark_mode else None,
                                  selectbackground=DARK_HIGHLIGHT,
                                  selectforeground=DARK_FG)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        
        # 导航按钮
        nav_frame = tk.Frame(frame, bg=DARK_BG if self.dark_mode else None)
        nav_frame.pack(fill=tk.X, pady=5)
        tk.Button(nav_frame, text="← 上一个", command=self.prev_image, width=10,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="下一个 →", command=self.next_image, width=10,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=2)
        tk.Button(nav_frame, text="删除", command=self.delete_image, width=10,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=2)
        
        # 状态标签
        self.status_label = tk.Label(frame, text="", fg="blue" if not self.dark_mode else "#4da6ff",
                                     bg=DARK_BG if self.dark_mode else None)
        self.status_label.pack()
    
    def bind_drag_drop(self, container):
        """绑定拖拽事件"""
        container.drop_target_register(DND_FILES)
        container.dnd_bind('<<Drop>>', self.on_drop)
        container.dnd_bind('<<DragEnter>>', self.on_drag_enter)
        container.dnd_bind('<<DragLeave>>', self.on_drag_leave)
    
    def on_drop(self, event):
        """处理文件夹拖拽放置"""
        # 获取拖拽的路径
        path = event.data
        # 清理路径（去除引号）
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        
        # 验证是否为文件夹
        if os.path.isdir(path):
            self.folder_path.set(path)
            self.refresh_images()
            self.status_label.config(text=f"已导入：{path}")
        else:
            messagebox.showwarning("警告", "请拖拽文件夹，而不是文件")
    
    def on_drag_enter(self, event):
        """拖拽进入时的高亮效果"""
        self.image_label.config(bg=DARK_HIGHLIGHT)
    
    def on_drag_leave(self, event):
        """拖拽离开时恢复原色"""
        self.image_label.config(bg=DARK_CONTAINER_BG)
    
    def select_folder(self):
        """选择文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.refresh_images()
    
    def refresh_images(self):
        """刷新图片列表"""
        folder = self.folder_path.get()
        if not folder or not os.path.exists(folder):
            return
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
        self.image_files = [f for f in os.listdir(folder) 
                           if Path(f).suffix.lower() in image_extensions]
        self.image_files.sort()
        
        self.listbox.delete(0, tk.END)
        for img in self.image_files:
            self.listbox.insert(tk.END, img)
        
        self.current_index = 0
        if self.image_files:
            self.show_image(0)
        else:
            self.clear_preview()
        
        self.update_status()
        self.update_listbox_colors()  # 更新列表颜色
    
    def on_select(self, event):
        """列表选择事件"""
        selection = self.listbox.curselection()
        if selection:
            self.current_index = selection[0]
            self.show_image(self.current_index)
    
    def show_image(self, index):
        """显示指定索引的图片"""
        if not self.image_files or index < 0 or index >= len(self.image_files):
            return
        
        folder = self.folder_path.get()
        image_path = os.path.join(folder, self.image_files[index])
        
        try:
            # 加载图片
            img = Image.open(image_path)
            # 获取展示框的实际尺寸
            label_width = self.image_label.winfo_width()
            label_height = self.image_label.winfo_height()
            # 根据展示框大小自适应缩放（留出一些边距）
            if label_width > 1 and label_height > 1:
                img.thumbnail((label_width - 20, label_height - 20))
            else:
                # 如果窗口还未渲染完成，使用默认尺寸
                img.thumbnail((1000, 800))
            self.current_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_image, text="")
        except Exception as e:
            self.image_label.config(image="", text=f"加载失败：{str(e)}")
        
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.update_status()
        self.update_listbox_colors()  # 更新列表颜色
        
        # 图片变化时恢复导出按钮状态
        if self.main_window and hasattr(self.main_window, 'enable_export_button'):
            self.main_window.enable_export_button()
    
    def clear_preview(self):
        """清除预览"""
        self.image_label.config(image="", text="暂无图片")
        self.current_image = None
    
    def prev_image(self):
        """上一个图片"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image(self.current_index)
    
    def next_image(self):
        """下一个图片"""
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.show_image(self.current_index)
    
    def delete_image(self):
        """删除当前选中的图片"""
        if not self.image_files or self.current_index >= len(self.image_files):
            messagebox.showwarning("警告", "没有可删除的图片")
            return
        
        folder = self.folder_path.get()
        image_name = self.image_files[self.current_index]
        image_path = os.path.join(folder, image_name)
        
        if messagebox.askyesno("确认", f"确定要删除 {image_name} 吗？"):
            try:
                os.remove(image_path)
                self.image_files.pop(self.current_index)
                self.listbox.delete(self.current_index)
                
                # 调整索引
                if self.current_index >= len(self.image_files):
                    self.current_index = max(0, len(self.image_files) - 1)
                
                if self.image_files:
                    self.show_image(self.current_index)
                else:
                    self.clear_preview()
                
                self.update_status()
            except Exception as e:
                messagebox.showerror("错误", f"删除失败：{str(e)}")
    
    def get_current_image_path(self):
        """获取当前图片路径"""
        if not self.image_files or self.current_index >= len(self.image_files):
            return None
        folder = self.folder_path.get()
        return os.path.join(folder, self.image_files[self.current_index])
    
    def update_status(self):
        """更新状态显示"""
        if self.image_files:
            self.status_label.config(text=f"当前：{self.current_index + 1}/{len(self.image_files)}",
                                     fg="blue" if not self.dark_mode else "#4da6ff")
        else:
            self.status_label.config(text="无图片",
                                     fg="blue" if not self.dark_mode else "#4da6ff")
    
    def mark_as_paired(self, image_name):
        """标记图片为已配对"""
        self.paired_images.add(image_name)
        self.update_listbox_colors()
    
    def update_listbox_colors(self):
        """更新列表项颜色，已配对的图片高亮显示"""
        for i, image_name in enumerate(self.image_files):
            if image_name in self.paired_images:
                # 已配对的图片使用绿色背景
                self.listbox.itemconfig(i, bg='#2d7a3e', fg='white')
            else:
                # 未配对的图片使用默认背景
                self.listbox.itemconfig(i, bg=DARK_ENTRY_BG if self.dark_mode else None, 
                                        fg=DARK_FG if self.dark_mode else None)


class ImagePairToolGUI:
    """图片配对工具 GUI 界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("双面板图片配对工具 - 深色模式")
        self.root.geometry("1200x1100")
        
        # 设置深色模式
        self.dark_mode = True
        self.setup_dark_mode()
        
        self.export_folder = tk.StringVar()
        self.export_disabled = False  # 导出按钮禁用状态标记
        
        # 进度条变量
        self.progress_var = tk.DoubleVar()
        
        self.create_widgets()
    
    def setup_dark_mode(self):
        """设置深色模式"""
        if self.dark_mode:
            self.root.config(bg=DARK_BG)
            # 设置样式
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('TFrame', background=DARK_BG)
            style.configure('TLabel', background=DARK_BG, foreground=DARK_FG)
            style.configure('TButton', background=DARK_BUTTON_BG, foreground=DARK_BUTTON_FG)
    
    def create_widgets(self):
        """创建界面组件"""
        # 顶部工具栏
        toolbar = tk.Frame(self.root, pady=10, bg=DARK_BG if self.dark_mode else None)
        toolbar.pack(fill=tk.X, padx=10)
        
        tk.Label(toolbar, text="导出文件夹:", width=12,
                 bg=DARK_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT)
        tk.Entry(toolbar, textvariable=self.export_folder, width=40,
                 bg=DARK_ENTRY_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="浏览", command=self.select_export_folder, width=8,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT)
        
        # 同步下一张按钮
        tk.Button(toolbar, text="同步下一张", command=self.sync_next_image, width=15,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.RIGHT, padx=5)
        
        # 同步上一张按钮
        tk.Button(toolbar, text="同步上一张", command=self.sync_prev_image, width=15,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.RIGHT, padx=5)
        
        # 同步删除按钮
        tk.Button(toolbar, text="同步删除", command=self.sync_delete_images, width=15,
                  bg="#d9534f" if self.dark_mode else "#d9534f",
                  fg="white").pack(side=tk.RIGHT, padx=5)
        
        # 一键自动配对按钮
        tk.Button(toolbar, text="一键自动配对", command=self.auto_pair_all, width=15,
                  bg="#0078d4" if self.dark_mode else "#0078d4",
                  fg="white").pack(side=tk.RIGHT, padx=5)
        
        # 导出按钮
        self.export_button = tk.Button(toolbar, text="导出配对", command=self.export_pairs, 
                                       width=15, bg="#2d7a3e" if self.dark_mode else "#4CAF50", 
                                       fg="white")
        self.export_button.pack(side=tk.RIGHT, padx=10)
        
        # 中间双面板区域
        panel_frame = tk.Frame(self.root, bg=DARK_BG if self.dark_mode else None)
        panel_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧面板
        self.left_panel = ImagePanel(panel_frame, "左侧面板 (control)", tk.LEFT, 
                                     self, dark_mode=self.dark_mode)
        
        # 右侧面板
        self.right_panel = ImagePanel(panel_frame, "右侧面板 (target)", tk.RIGHT,
                                      self, dark_mode=self.dark_mode)
        
        # 进度条区域 (新增)
        progress_frame = tk.Frame(self.root, pady=5, bg=DARK_BG if self.dark_mode else None)
        progress_frame.pack(fill=tk.X, padx=10)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                            maximum=100, mode='determinate',
                                            style='dark.Horizontal.TProgressbar' if self.dark_mode else 'Horizontal.TProgressbar')
        self.progress_bar.pack(fill=tk.X)
        
        # 配置进度条样式 (深色模式)
        if self.dark_mode:
            style = ttk.Style()
            style.configure('dark.Horizontal.TProgressbar', 
                            background=DARK_HIGHLIGHT, 
                            troughcolor=DARK_ENTRY_BG,
                            bordercolor=DARK_BG,
                            lightcolor=DARK_HIGHLIGHT,
                            darkcolor=DARK_HIGHLIGHT)

        # 底部状态栏
        status_frame = tk.Frame(self.root, pady=5, bg=DARK_BG if self.dark_mode else None)
        status_frame.pack(fill=tk.X, padx=10)
        self.status_label = tk.Label(status_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W,
                                     bg=DARK_ENTRY_BG if self.dark_mode else None,
                                     fg=DARK_FG if self.dark_mode else None)
        self.status_label.pack(fill=tk.X)
        
        # 如果 DND 不可用，显示提示
        if not DND_AVAILABLE and self.dark_mode:
            hint_label = tk.Label(self.root, 
                                  text="提示：安装 tkinterdnd2 可启用拖拽功能 (pip install tkinterdnd2)",
                                  fg="#888888", bg=DARK_BG)
            hint_label.pack(pady=5)
    
    def enable_export_button(self):
        """恢复导出按钮为可点击状态"""
        if self.export_disabled:
            self.export_button.config(state=tk.NORMAL, bg="#2d7a3e" if self.dark_mode else "#4CAF50")
            self.export_disabled = False
    
    def disable_export_button(self):
        """禁用导出按钮"""
        self.export_button.config(state=tk.DISABLED, bg="#666666")
        self.export_disabled = True
    
    def select_export_folder(self):
        """选择导出文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.export_folder.set(folder)
    
    def sync_next_image(self):
        """两侧面板同时切换到下一张图片"""
        left_has_next = self.left_panel.current_index < len(self.left_panel.image_files) - 1
        right_has_next = self.right_panel.current_index < len(self.right_panel.image_files) - 1
        
        if not left_has_next and not right_has_next:
            messagebox.showinfo("提示", "两侧都已到最后一张图片")
            return
        
        if left_has_next:
            self.left_panel.next_image()
        if right_has_next:
            self.right_panel.next_image()
        
        # 更新状态提示
        left_info = f"左:{self.left_panel.current_index + 1}/{len(self.left_panel.image_files)}" if self.left_panel.image_files else "左:无"
        right_info = f"右:{self.right_panel.current_index + 1}/{len(self.right_panel.image_files)}" if self.right_panel.image_files else "右:无"
        self.status_label.config(text=f"✓ 同步切换完成 | {left_info} | {right_info}")
    
    def sync_prev_image(self):
        """两侧面板同时切换到上一张图片"""
        left_has_prev = self.left_panel.current_index > 0
        right_has_prev = self.right_panel.current_index > 0
        
        if not left_has_prev and not right_has_prev:
            messagebox.showinfo("提示", "两侧都已到第一张图片")
            return
        
        if left_has_prev:
            self.left_panel.prev_image()
        if right_has_prev:
            self.right_panel.prev_image()
        
        # 更新状态提示
        left_info = f"左:{self.left_panel.current_index + 1}/{len(self.left_panel.image_files)}" if self.left_panel.image_files else "左:无"
        right_info = f"右:{self.right_panel.current_index + 1}/{len(self.right_panel.image_files)}" if self.right_panel.image_files else "右:无"
        self.status_label.config(text=f"✓ 同步切换完成 | {left_info} | {right_info}")
    
    def sync_delete_images(self):
        """同时删除左右两侧选中的图片"""
        left_path = self.left_panel.get_current_image_path()
        right_path = self.right_panel.get_current_image_path()
        
        if not left_path and not right_path:
            messagebox.showwarning("警告", "两侧都没有可删除的图片")
            return
        
        left_name = Path(left_path).name if left_path else "无"
        right_name = Path(right_path).name if right_path else "无"
        
        confirm_msg = f"确定要删除以下图片吗？\n\n左侧：{left_name}\n右侧：{right_name}"
        if not messagebox.askyesno("确认", confirm_msg):
            return
        
        # 删除左侧图片
        if left_path and os.path.exists(left_path):
            try:
                os.remove(left_path)
                self.left_panel.image_files.pop(self.left_panel.current_index)
                self.left_panel.listbox.delete(self.left_panel.current_index)
                # 调整索引
                if self.left_panel.current_index >= len(self.left_panel.image_files):
                    self.left_panel.current_index = max(0, len(self.left_panel.image_files) - 1)
                if self.left_panel.image_files:
                    self.left_panel.show_image(self.left_panel.current_index)
                else:
                    self.left_panel.clear_preview()
                self.left_panel.update_status()
            except Exception as e:
                messagebox.showerror("错误", f"左侧删除失败：{str(e)}")
                return
        
        # 删除右侧图片
        if right_path and os.path.exists(right_path):
            try:
                os.remove(right_path)
                self.right_panel.image_files.pop(self.right_panel.current_index)
                self.right_panel.listbox.delete(self.right_panel.current_index)
                # 调整索引
                if self.right_panel.current_index >= len(self.right_panel.image_files):
                    self.right_panel.current_index = max(0, len(self.right_panel.image_files) - 1)
                if self.right_panel.image_files:
                    self.right_panel.show_image(self.right_panel.current_index)
                else:
                    self.right_panel.clear_preview()
                self.right_panel.update_status()
            except Exception as e:
                messagebox.showerror("错误", f"右侧删除失败：{str(e)}")
                return
        
        # 更新状态提示
        left_info = f"左:{self.left_panel.current_index + 1}/{len(self.left_panel.image_files)}" if self.left_panel.image_files else "左:无"
        right_info = f"右:{self.right_panel.current_index + 1}/{len(self.right_panel.image_files)}" if self.right_panel.image_files else "右:无"
        self.status_label.config(text=f"✓ 同步删除完成 | {left_info} | {right_info}")
        
        # 图片变化时恢复导出按钮状态
        self.enable_export_button()
    
    def auto_pair_all(self):
        """一键自动配对所有同名文件并导出 (多线程优化版)"""
        export_folder = self.export_folder.get()
        
        if not export_folder:
            messagebox.showerror("错误", "请先选择导出文件夹")
            return
        
        left_folder = self.left_panel.folder_path.get()
        right_folder = self.right_panel.folder_path.get()
        
        if not left_folder or not os.path.exists(left_folder):
            messagebox.showerror("错误", "左侧面板未选择有效文件夹")
            return
        
        if not right_folder or not os.path.exists(right_folder):
            messagebox.showerror("错误", "右侧面板未选择有效文件夹")
            return
        
        # 获取左右两侧的图片文件列表
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp']
        left_files = set(f for f in os.listdir(left_folder) 
                        if Path(f).suffix.lower() in image_extensions)
        right_files = set(f for f in os.listdir(right_folder) 
                         if Path(f).suffix.lower() in image_extensions)
        
        # 找出同名文件
        common_files = left_files & right_files
        
        if not common_files:
            messagebox.showinfo("提示", "没有找到同名文件")
            return
        
        # 确认对话框
        confirm_msg = f"找到 {len(common_files)} 对同名文件，是否全部导出？\n\n将调整分辨率为两者中的较小值，并分别保存到 control 和 target 文件夹。\n(已启用多线程加速)"
        if not messagebox.askyesno("确认", confirm_msg):
            return
        
        # 创建导出子文件夹
        control_folder = os.path.join(export_folder, "control")
        target_folder = os.path.join(export_folder, "target")
        os.makedirs(control_folder, exist_ok=True)
        os.makedirs(target_folder, exist_ok=True)
        
        # 排序文件列表
        sorted_files = sorted(common_files)
        total_count = len(sorted_files)
        
        # 重置进度条和状态
        self.progress_var.set(0)
        self.status_label.config(text=f"正在初始化线程池...")
        self.root.update()
        
        success_count = 0
        error_count = 0
        errors = []
        paired_files = [] # 记录成功配对的文件名
        
        # 定义单个文件处理函数
        def process_pair(filename):
            left_path = os.path.join(left_folder, filename)
            right_path = os.path.join(right_folder, filename)
            
            try:
                # 打开图片
                img_left = Image.open(left_path)
                img_right = Image.open(right_path)
                
                # 获取原始尺寸
                w1, h1 = img_left.size
                w2, h2 = img_right.size
                
                # 计算目标分辨率（取两者中的较小宽和较小高）
                target_w = min(w1, w2)
                target_h = min(h1, h2)
                
                # 调整分辨率 (使用 LANCZOS 滤镜保证质量)
                img_left_resized = img_left.resize((target_w, target_h), Image.LANCZOS)
                img_right_resized = img_right.resize((target_w, target_h), Image.LANCZOS)
                
                # 保存左图到 control 文件夹
                control_dest = os.path.join(control_folder, filename)
                img_left_resized.save(control_dest)
                
                # 保存右图 to target 文件夹
                target_dest = os.path.join(target_folder, filename)
                img_right_resized.save(target_dest)
                
                return (filename, True, None)
                
            except Exception as e:
                return (filename, False, str(e))

        # 使用线程池执行任务
        # max_workers 默认为 CPU 核心数 * 5，对于 IO 密集型任务通常足够，也可手动指定如 8 或 16
        with ThreadPoolExecutor() as executor:
            future_to_file = {executor.submit(process_pair, fname): fname for fname in sorted_files}
            
            completed = 0
            for future in as_completed(future_to_file):
                filename, success, error_msg = future.result()
                completed += 1
                
                if success:
                    success_count += 1
                    paired_files.append(filename)
                else:
                    error_count += 1
                    errors.append(f"{filename}: {error_msg}")
                
                # 更新进度条和状态 (在主线程中更新 UI 是安全的，因为这是在 main thread 调用的循环中)
                progress_percent = (completed / total_count) * 100
                self.progress_var.set(progress_percent)
                self.status_label.config(text=f"正在处理 {completed}/{total_count}... 成功:{success_count} 失败:{error_count}")
                self.root.update_idletasks() # 强制刷新 UI
        
        # 显示结果
        if error_count == 0:
            messagebox.showinfo("完成", f"成功导出 {success_count} 对图片！\n所有文件已调整分辨率并保存到:\n- {control_folder}\n- {target_folder}")
        else:
            error_details = "\n".join(errors[:5])  # 只显示前 5 个错误
            if error_count > 5:
                error_details += f"\n... 还有 {error_count - 5} 个错误"
            messagebox.showwarning("部分完成", 
                                   f"成功导出 {success_count} 对图片，失败 {error_count} 对。\n\n错误详情:\n{error_details}")
        
        self.status_label.config(text=f"✓ 自动配对完成 | 成功:{success_count} | 失败:{error_count}")
        
        # 批量标记为已配对并刷新列表颜色
        for fname in paired_files:
            self.left_panel.mark_as_paired(fname)
            self.right_panel.mark_as_paired(fname)
        
        self.left_panel.update_listbox_colors()
        self.right_panel.update_listbox_colors()
        
        # 完成后重置进度条（可选，或者保持在 100%）
        # self.progress_var.set(0) 

    def export_pairs(self):
        """导出配对图片（调整分辨率后分别保存）"""
        export_folder = self.export_folder.get()
        
        if not export_folder:
            messagebox.showerror("错误", "请选择导出文件夹")
            return
        
        left_path = self.left_panel.get_current_image_path()
        right_path = self.right_panel.get_current_image_path()
        
        if not left_path:
            messagebox.showerror("错误", "左侧面板没有选中的图片")
            return
        
        if not right_path:
            messagebox.showerror("错误", "右侧面板没有选中的图片")
            return
        
        # 创建导出子文件夹
        control_folder = os.path.join(export_folder, "control")
        target_folder = os.path.join(export_folder, "target")
        os.makedirs(control_folder, exist_ok=True)
        os.makedirs(target_folder, exist_ok=True)
        
        # 获取文件名 - 使用左侧图片文件名作为统一文件名
        left_name = Path(left_path).name
        right_name = Path(right_path).name
        # 导出时使用相同的文件名
        export_name = left_name
        
        try:
            # 打开图片
            img_left = Image.open(left_path)
            img_right = Image.open(right_path)
            
            # 获取原始尺寸
            w1, h1 = img_left.size
            w2, h2 = img_right.size
            
            # 计算目标分辨率（取两者中的较小宽和较小高）
            target_w = min(w1, w2)
            target_h = min(h1, h2)
            
            # 调整分辨率 (使用 LANCZOS 滤镜保证质量)
            img_left_resized = img_left.resize((target_w, target_h), Image.LANCZOS)
            img_right_resized = img_right.resize((target_w, target_h), Image.LANCZOS)
            
            # 保存左图到 control 文件夹
            control_dest = os.path.join(control_folder, export_name)
            img_left_resized.save(control_dest)
            
            # 保存右图到 target 文件夹
            target_dest = os.path.join(target_folder, export_name)
            img_right_resized.save(target_dest)
            
            self.status_label.config(text=f"✓ 已导出并调整分辨率：{export_name} ({target_w}x{target_h}) | 切换图片后可再次导出")
            # 禁用导出按钮，防止重复导出
            self.disable_export_button()
            
            # 标记左右面板当前图片为已配对
            self.left_panel.mark_as_paired(left_name)
            self.right_panel.mark_as_paired(right_name)
            
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
            self.status_label.config(text="导出失败")


def main():
    """主函数"""
    # 根据 DND 可用性选择根窗口类型
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    
    # 设置窗口背景色
    root.config(bg=DARK_BG)
    
    app = ImagePairToolGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()