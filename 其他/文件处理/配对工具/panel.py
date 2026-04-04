#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双面板图片配对工具 - 图片面板类
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
from pathlib import Path
from PIL import Image, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

from config import (
    DARK_BG, DARK_FG, DARK_ENTRY_BG, DARK_BUTTON_BG, DARK_BUTTON_FG,
    DARK_CONTAINER_BG, DARK_HIGHLIGHT, IMAGE_AREA_HEIGHT
)
from utils import get_image_files


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

        # 图片展示框
        image_container = tk.Frame(frame, relief=tk.SUNKEN, borderwidth=2,
                                   bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0")
        image_container.pack(fill=tk.BOTH, expand=True, pady=5, padx=0)
        image_container.pack_propagate(False)
        image_container.config(height=IMAGE_AREA_HEIGHT)

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
        path = event.data

        # 清理路径：去除引号
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]

        # 清理路径：去除 file:// 前缀
        if path.startswith('file://'):
            path = path[7:]
            from urllib.parse import unquote
            path = unquote(path)

        # 清理路径：处理 Windows 特有的 {path} 格式
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]

        # 处理多路径情况
        paths = []
        if '\n' in path:
            paths = path.split('\n')
        elif ' ' in path and not os.path.exists(path):
            paths = path.split(' ')
        else:
            paths = [path]

        valid_folder = None
        for p in paths:
            p = p.strip()
            if not p:
                continue
            if p.startswith('"') and p.endswith('"'):
                p = p[1:-1]
            if os.path.isdir(p):
                valid_folder = p
                break

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
        self.image_files = get_image_files(folder)
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
        self.update_listbox_colors()

    def on_select(self, event):
        """列表选择事件 - 点击图片时检测另一侧同名文件并选中"""
        selection = self.listbox.curselection()
        if selection:
            self.current_index = selection[0]
            selected_filename = self.image_files[self.current_index]

            main_window = getattr(self, 'main_window', None)
            other_panel = None

            if main_window and hasattr(main_window, 'left_panel') and hasattr(main_window, 'right_panel'):
                if self == main_window.left_panel:
                    other_panel = main_window.right_panel
                elif self == main_window.right_panel:
                    other_panel = main_window.left_panel

            if other_panel and other_panel.image_files:
                try:
                    other_index = other_panel.image_files.index(selected_filename)
                    if other_panel.current_index != other_index:
                        other_panel.current_index = other_index
                        other_panel.show_image(other_index)
                        other_panel.listbox.selection_clear(0, tk.END)
                        other_panel.listbox.selection_set(other_index)
                except ValueError:
                    pass

            self.show_image(self.current_index)

    def show_image(self, index):
        """显示指定索引的图片"""
        if not self.image_files or index < 0 or index >= len(self.image_files):
            return

        folder = self.folder_path.get()
        image_path = os.path.join(folder, self.image_files[index])

        try:
            img = Image.open(image_path)
            original_width, original_height = img.size

            label_width = self.image_label.winfo_width()
            label_height = self.image_label.winfo_height()

            if label_width > 1 and label_height > 1:
                img.thumbnail((label_width - 20, label_height - 20))
            else:
                img.thumbnail((1000, 800))

            self.current_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_image, text="")

            self.update_status_with_resolution(original_width, original_height)
        except Exception as e:
            self.image_label.config(image="", text=f"加载失败：{str(e)}")

        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.update_listbox_colors()

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
                self.listbox.itemconfig(i, bg='#2d7a3e', fg='white')
            else:
                self.listbox.itemconfig(i, bg=DARK_ENTRY_BG if self.dark_mode else None,
                                        fg=DARK_FG if self.dark_mode else None)
