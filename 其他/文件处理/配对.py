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
        # 修改：移除 padx 使左右贴边，设置 expand=True 让容器尽可能扩展以靠近中间
        image_container.pack(fill=tk.BOTH, expand=True, pady=5, padx=0)
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
                                    width=80, height=50,
                                    anchor=tk.E if self.side == tk.LEFT else tk.W)
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
        # 获取拖拽的数据
        path = event.data
        
        # 清理路径：去除引号
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        
        # 清理路径：去除 file:// 前缀 (常见于 Linux/Mac 或某些 DND 实现)
        if path.startswith('file://'):
            path = path[7:]
            # URL 解码处理（可选，针对含空格或特殊字符的路径）
            from urllib.parse import unquote
            path = unquote(path)
        
        # 清理路径：处理 Windows 特有的 {path} 格式
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        
        # 处理多路径情况：某些系统拖拽多个项目时会用空格或换行分隔
        # 我们只取第一个有效的文件夹路径
        paths = []
        if '\n' in path:
            paths = path.split('\n')
        elif ' ' in path and not os.path.exists(path): 
            # 如果整个字符串不是有效路径，尝试按空格分割（注意：合法路径也可能含空格，所以先判断整体是否存在）
            paths = path.split(' ')
        else:
            paths = [path]
        
        valid_folder = None
        for p in paths:
            p = p.strip()
            if not p:
                continue
            # 再次去除可能的引号（分割后可能残留）
            if p.startswith('"') and p.endswith('"'):
                p = p[1:-1]
            if os.path.isdir(p):
                valid_folder = p
                break
        
        # 验证是否为文件夹
        if valid_folder:
            self.folder_path.set(valid_folder)
            self.refresh_images()
            self.status_label.config(text=f"已导入：{valid_folder}")
        else:
            messagebox.showwarning("警告", "请拖拽文件夹，而不是文件\n(未能识别到有效的文件夹路径)")
    
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
        """列表选择事件 - 点击图片时检测另一侧同名文件并选中"""
        selection = self.listbox.curselection()
        if selection:
            self.current_index = selection[0]
            selected_filename = self.image_files[self.current_index]
            
            # 尝试获取主窗口和另一侧面板以进行配对检测
            main_window = getattr(self, 'main_window', None)
            other_panel = None
            
            if main_window and hasattr(main_window, 'left_panel') and hasattr(main_window, 'right_panel'):
                if self == main_window.left_panel:
                    other_panel = main_window.right_panel
                elif self == main_window.right_panel:
                    other_panel = main_window.left_panel
            
            # 检查另一侧是否有同名文件并选中
            if other_panel and other_panel.image_files:
                try:
                    other_index = other_panel.image_files.index(selected_filename)
                    # 如果另一侧当前选中的不是这个文件，则切换过去显示
                    if other_panel.current_index != other_index:
                        other_panel.current_index = other_index
                        other_panel.show_image(other_index)
                        # 清除之前的选择并设置新的选择
                        other_panel.listbox.selection_clear(0, tk.END)
                        other_panel.listbox.selection_set(other_index)
                except ValueError:
                    # 另一侧没有同名文件，忽略
                    pass
            
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
            # 获取原始分辨率
            original_width, original_height = img.size
            
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
            
            # 更新状态显示分辨率信息
            self.update_status_with_resolution(original_width, original_height)
        except Exception as e:
            self.image_label.config(image="", text=f"加载失败：{str(e)}")
        
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        # 不再在此处调用 update_status()，因为已在 try 块中调用 update_status_with_resolution
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

    def update_status_with_resolution(self, width, height):
        """更新状态显示，包含分辨率信息"""
        if self.image_files:
            self.status_label.config(text=f"当前：{self.current_index + 1}/{len(self.image_files)} | 分辨率：{width}x{height}",
                                     fg="blue" if not self.dark_mode else "#4da6ff")
        else:
            self.status_label.config(text=f"无图片 | 分辨率：{width}x{height}",
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
        
        # 新增：左图覆盖右图按钮
        tk.Button(toolbar, text="左图覆盖右图", command=self.copy_left_to_right, width=15,
                  bg="#d98e04" if self.dark_mode else "#d98e04",
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
    
    def copy_left_to_right(self):
        """将当前左图复制并覆盖右图"""
        left_path = self.left_panel.get_current_image_path()
        right_path = self.right_panel.get_current_image_path()
        
        if not left_path:
            messagebox.showwarning("警告", "左侧面板没有选中的图片")
            return
        
        if not right_path:
            messagebox.showwarning("警告", "右侧面板没有选中的图片，无法覆盖")
            return
        
        left_name = Path(left_path).name
        right_name = Path(right_path).name
        
        confirm_msg = f"确定要用左图覆盖右图吗？\n\n源文件：{left_name}\n目标文件：{right_name}\n\n注意：右侧原文件将被永久替换！"
        if not messagebox.askyesno("确认", confirm_msg):
            return
        
        try:
            # 复制左图到右图路径（覆盖）
            shutil.copy2(left_path, right_path)
            
            # 刷新右侧面板以显示新图片
            self.right_panel.refresh_images()
            
            # 尝试在刷新后重新选中对应索引的图片（如果文件名没变，索引通常不变；如果变了，refresh_images会重置索引到0或尝试保持）
            # 由于我们是覆盖同名文件（逻辑上通常是用左图内容替换右图内容，但文件名保持右侧的文件名），
            # 如果用户希望右侧文件名也变成左侧的，逻辑会复杂些。
            # 根据需求“复制一份左图文件到右图文件夹里去替换右图文件”，通常指内容替换，文件名保持右侧当前文件名。
            # 如果右侧文件列表顺序因刷新而改变，current_index 可能需要重新定位。
            # 这里简单处理：refresh_images 后，如果原文件名还在，尝试选中它。
            # 但因为是覆盖，文件名没变，所以 current_index 应该还是指向那个位置，除非文件被删了又加（copy2不会导致文件名变化）。
            # 为了保险，我们根据文件名重新定位右侧当前索引
            if right_name in self.right_panel.image_files:
                new_index = self.right_panel.image_files.index(right_name)
                self.right_panel.current_index = new_index
                self.right_panel.show_image(new_index)
                self.right_panel.listbox.selection_clear(0, tk.END)
                self.right_panel.listbox.selection_set(new_index)
            
            self.status_label.config(text=f"✓ 已用左图 ({left_name}) 覆盖右图 ({right_name})")
            
            # 图片变化时恢复导出按钮状态
            self.enable_export_button()
            
        except Exception as e:
            messagebox.showerror("错误", f"覆盖失败：{str(e)}")
            self.status_label.config(text="覆盖失败")

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
        
        # 询问是否进行比例填充
        fill_ratio = messagebox.askyesno(
            "图片比例填充选项",
            "是否将图片统一调整为 1:1 正方形，并使用白色背景填充？\n\n是：所有图片将以白色背景填充为 1:1 正方形\n否：仅调整尺寸为两者中的较小值"
        )
        
        # 确认对话框
        fill_text = "并填充为 1:1 白色背景" if fill_ratio else ""
        confirm_msg = f"找到 {len(common_files)} 对同名文件，是否全部导出？\n\n将调整分辨率为两者中的较小值{fill_text}，并分别保存到 control 和 target 文件夹。\n(已启用多线程加速)"
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
        
        def fill_image_with_background(img, target_size, bg_color=(255, 255, 255)):
            """将图片居中放置到指定尺寸的白色背景上"""
            target_w, target_h = target_size
            
            # 创建带 Alpha 通道的图像用于计算
            img_rgba = img.convert('RGBA')
            width, height = img.size
            
            # 计算缩放比例，确保图片完整显示在目标区域内（保持宽高比）
            scale = min(target_w / width, target_h / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 缩放图片
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 创建白色背景图像
            background = Image.new('RGBA', (target_w, target_h), bg_color + (255,))
            
            # 计算居中位置
            paste_x = (target_w - new_width) // 2
            paste_y = (target_h - new_height) // 2
            
            # 将缩放后的图片粘贴到背景中央
            background.paste(img_resized, (paste_x, paste_y), img_resized if img.mode == 'RGBA' else None)
            
            return background.convert('RGB')

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
                
                if fill_ratio:
                    # 填充为 1:1 正方形，白色背景
                    target_square_size = max(target_w, target_h)
                    img_left_processed = fill_image_with_background(img_left, (target_square_size, target_square_size))
                    img_right_processed = fill_image_with_background(img_right, (target_square_size, target_square_size))
                else:
                    # 仅调整尺寸为两者中的较小值
                    img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                    img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)
                
                # 保存左图到 control 文件夹
                control_dest = os.path.join(control_folder, filename)
                img_left_processed.save(control_dest)
                
                # 保存右图 to target 文件夹
                target_dest = os.path.join(target_folder, filename)
                img_right_processed.save(target_dest)
                
                return (filename, True, None)
                
            except Exception as e:
                return (filename, False, str(e))

        # 使用线程池执行任务
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
                
                progress_percent = (completed / total_count) * 100
                self.progress_var.set(progress_percent)
                self.status_label.config(text=f"正在处理 {completed}/{total_count}... 成功:{success_count} 失败:{error_count}")
                self.root.update_idletasks()
        
        # 显示结果
        if error_count == 0:
            fill_info = "（已填充为 1:1 白色背景）" if fill_ratio else ""
            messagebox.showinfo("完成", f"成功导出 {success_count} 对图片！{fill_info}\n所有文件保存到:\n- {control_folder}\n- {target_folder}")
        else:
            error_details = "\n".join(errors[:5])
            if error_count > 5:
                error_details += f"\n... 还有 {error_count - 5} 个错误"
            messagebox.showwarning("部分完成", 
                                   f"成功导出 {success_count} 对图片，失败 {error_count} 对。\n\n错误详情:\n{error_details}")
        
        self.status_label.config(text=f"✓ 自动配对完成 | 成功:{success_count} | 失败:{error_count}")
        
        for fname in paired_files:
            self.left_panel.mark_as_paired(fname)
            self.right_panel.mark_as_paired(fname)
        
        self.left_panel.update_listbox_colors()
        self.right_panel.update_listbox_colors()

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
        
        # 询问是否进行比例填充
        fill_ratio = messagebox.askyesno(
            "图片比例填充选项",
            "是否将图片统一调整为 1:1 正方形，并使用白色背景填充？\n\n是：所有图片将以白色背景填充为 1:1 正方形\n否：仅调整尺寸为两者中的较小值"
        )
        
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
        
        def fill_image_with_background(img, target_size, bg_color=(255, 255, 255)):
            """将图片居中放置到指定尺寸的白色背景上"""
            target_w, target_h = target_size
            
            # 创建带 Alpha 通道的图像用于计算
            img_rgba = img.convert('RGBA')
            width, height = img.size
            
            # 计算缩放比例，确保图片完整显示在目标区域内（保持宽高比）
            scale = min(target_w / width, target_h / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            # 缩放图片
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 创建白色背景图像
            background = Image.new('RGBA', (target_w, target_h), bg_color + (255,))
            
            # 计算居中位置
            paste_x = (target_w - new_width) // 2
            paste_y = (target_h - new_height) // 2
            
            # 将缩放后的图片粘贴到背景中央
            background.paste(img_resized, (paste_x, paste_y), img_resized if img.mode == 'RGBA' else None)
            
            return background.convert('RGB')
        
        try:
            # 打开图片
            img_left = Image.open(left_path)
            img_right = Image.open(right_path)
            
            # 获取原始尺寸
            w1, h1 = img_left.size
            w2, h2 = img_right.size
            
            if fill_ratio:
                # 填充为 1:1 正方形，白色背景
                target_square_size = max(w1, w2, h1, h2)
                img_left_processed = fill_image_with_background(img_left, (target_square_size, target_square_size))
                img_right_processed = fill_image_with_background(img_right, (target_square_size, target_square_size))
                final_size = f"{target_square_size}x{target_square_size}"
            else:
                # 仅调整尺寸为两者中的较小宽和较小高
                target_w = min(w1, w2)
                target_h = min(h1, h2)
                img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)
                final_size = f"{target_w}x{target_h}"
            
            # 保存左图到 control 文件夹
            control_dest = os.path.join(control_folder, export_name)
            img_left_processed.save(control_dest)
            
            # 保存右图到 target 文件夹
            target_dest = os.path.join(target_folder, export_name)
            img_right_processed.save(target_dest)
            
            fill_text = "（已填充为 1:1 白色背景）" if fill_ratio else ""
            self.status_label.config(text=f"✓ 已导出{fill_text}：{export_name} ({final_size}) | 切换图片后可再次导出")
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
