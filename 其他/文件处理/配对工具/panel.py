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

    def __init__(self, parent, name, main_window, dark_mode=True, with_listbox=True, image_align=tk.E):
        self.parent = parent
        self.name = name
        self.main_window = main_window
        self.dark_mode = dark_mode
        self.with_listbox = with_listbox
        self.image_align = image_align  # 图片对齐方向：tk.E 靠右，tk.W 靠左
        self.folder_path = tk.StringVar()
        self.image_files = []
        self.current_index = 0
        self.current_image = None
        self.paired_images = set()  # 记录已配对的图片文件名

        # 缩放相关
        self.original_image = None  # 原始图片
        self.zoom_level = 1.0  # 缩放级别
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        # 拖拽相关
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.is_dragging = False

        self.create_widgets()

    def create_widgets(self):
        """创建面板组件"""
        # 面板框架
        if self.dark_mode:
            frame = tk.LabelFrame(self.parent, text=self.name, padx=10, pady=10,
                                  bg=DARK_BG, fg=DARK_FG)
        else:
            frame = tk.LabelFrame(self.parent, text=self.name, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # 文件夹选择和导航按钮（同一行）
        folder_frame = tk.Frame(frame, bg=DARK_BG if self.dark_mode else None)
        folder_frame.pack(fill=tk.X, pady=5)

        # 文件夹标签和输入框
        tk.Label(folder_frame, text="文件夹:", width=8,
                 bg=DARK_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT)
        tk.Entry(folder_frame, textvariable=self.folder_path, width=14,
                 bg=DARK_ENTRY_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=5)
        tk.Button(folder_frame, text="浏览", command=self.select_folder, width=6,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT)
        tk.Button(folder_frame, text="刷新", command=self.refresh_images, width=6,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=5)

        # 导航按钮
        tk.Button(folder_frame, text="← 上一个", command=self.prev_image, width=10,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=2)
        tk.Button(folder_frame, text="下一个 →", command=self.next_image, width=10,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=2)
        tk.Button(folder_frame, text="删除", command=self.delete_image, width=10,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=2)

        # 状态标签（右侧）
        self.status_label = tk.Label(folder_frame, text="", fg="blue" if not self.dark_mode else "#4da6ff",
                                     bg=DARK_BG if self.dark_mode else None)
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # 图片展示框
        image_container = tk.Frame(frame, relief=tk.SUNKEN, borderwidth=2,
                                   bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0")
        image_container.pack(fill=tk.BOTH, expand=True, pady=5, padx=0)
        image_container.pack_propagate(False)
        image_container.config(height=IMAGE_AREA_HEIGHT)

        # 创建 Canvas 用于支持拖拽和缩放
        self.image_canvas = tk.Canvas(image_container,
                                       bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0",
                                       highlightthickness=0)
        self.image_canvas.pack(fill=tk.BOTH, expand=True)

        # 添加拖拽功能提示标签
        if self.dark_mode:
            self.drag_hint = tk.Label(self.image_canvas, text="可拖拽移动图片 | 滚轮缩放",
                                bg=DARK_CONTAINER_BG, fg="#888888")
            self.drag_hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 在 Canvas 上创建图片（使用 create_image 而不是窗口）
        # 根据 image_align 设置锚点：tk.E=右侧图片从右对齐，tk.W=靠左对齐
        anchor = tk.NW if self.image_align == tk.W else tk.NE
        self.image_anchor = anchor  # 保存锚点用于后续缩放
        self.image_align_pos = 0 if self.image_align == tk.W else tk.RIGHT  # 保存对齐位置

        self.image_id = self.image_canvas.create_image(0, 0, anchor=anchor, image=None)

        # 绑定滚轮事件进行缩放
        self.image_canvas.bind('<MouseWheel>', self.on_mouse_wheel)
        self.image_canvas.bind('<Button-4>', self.on_mouse_wheel)
        self.image_canvas.bind('<Button-5>', self.on_mouse_wheel)

        # 绑定拖拽事件
        self.image_canvas.bind('<ButtonPress-1>', self.on_drag_start)
        self.image_canvas.bind('<B1-Motion>', self.on_drag_motion)
        self.image_canvas.bind('<ButtonRelease-1>', self.on_drag_end)

        # 绑定拖拽事件（如果支持）
        if DND_AVAILABLE and self.dark_mode:
            self.bind_drag_drop(image_container)

        # 图片列表（可选）
        if self.with_listbox:
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
        else:
            self.listbox = None

    def create_listbox(self, parent, height=10):
        """在指定父容器中创建列表框（用于外部布局）"""
        list_frame = tk.Frame(parent, bg=DARK_BG if self.dark_mode else None)
        list_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(list_frame, text=f"{self.name} - 图片列表:",
                 bg=DARK_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(anchor=tk.W)

        self.listbox = tk.Listbox(list_frame, height=height,
                                  bg=DARK_ENTRY_BG if self.dark_mode else None,
                                  fg=DARK_FG if self.dark_mode else None,
                                  selectbackground=DARK_HIGHLIGHT,
                                  selectforeground=DARK_FG)
        self.listbox.pack(fill=tk.BOTH, expand=True)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        return list_frame

    def on_drag_start(self, event):
        """开始拖拽"""
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        """拖拽移动"""
        if not self.is_dragging:
            return

        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y

        # 移动 Canvas 中的图片
        self.image_canvas.move(self.image_id, dx, dy)

        # 更新拖拽起始位置
        self.drag_start_x = event.x
        self.drag_start_y = event.y

        # 更新偏移量
        self.drag_offset_x += dx
        self.drag_offset_y += dy

    def on_drag_end(self, event):
        """结束拖拽"""
        self.is_dragging = False

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

            # 保存原始图片用于缩放
            self.original_image = img

            # 重置缩放和拖拽状态
            self.zoom_level = 1.0
            self.drag_offset_x = 0
            self.drag_offset_y = 0

            label_width = self.image_canvas.winfo_width()
            label_height = self.image_canvas.winfo_height()

            if label_width > 1 and label_height > 1:
                img.thumbnail((label_width - 20, label_height - 20))
            else:
                img.thumbnail((1000, 800))

            # 根据 image_align 设置图片位置
            if self.image_align == tk.W:
                # 左侧面板：图片靠左
                x_pos = 0
            else:
                # 右侧面板：图片靠右
                x_pos = label_width if label_width > 1 else self.image_canvas.winfo_reqwidth()

            self.image_canvas.coords(self.image_id, (x_pos, 0))

            # 显示图片
            self.current_image = ImageTk.PhotoImage(img)
            self.image_canvas.itemconfig(self.image_id, image=self.current_image)

            # 隐藏提示标签
            if hasattr(self, 'drag_hint'):
                self.drag_hint.place_forget()

            self.update_status_with_resolution(original_width, original_height)
        except Exception as e:
            self.image_canvas.itemconfig(self.image_id, image=None)
            self.drag_hint.config(text=f"加载失败：{str(e)}")
            self.drag_hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(index)
        self.update_listbox_colors()

        if self.main_window and hasattr(self.main_window, 'enable_export_button'):
            self.main_window.enable_export_button()

    def on_mouse_wheel(self, event):
        """处理鼠标滚轮缩放"""
        if self.original_image is None:
            return

        # Windows/Mac: event.delta, Linux: event.num (4=上滚，5=下滚)
        if hasattr(event, 'delta'):  # Windows/Mac
            delta = event.delta
        elif hasattr(event, 'num'):  # Linux
            delta = 120 if event.num == 4 else -120
        else:
            return

        # 计算新的缩放级别
        zoom_factor = 1.1 if delta > 0 else 0.9
        new_zoom = self.zoom_level * zoom_factor

        # 限制缩放范围
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return

        self.zoom_level = new_zoom

        # 应用缩放
        new_width = int(self.original_image.width * self.zoom_level)
        new_height = int(self.original_image.height * self.zoom_level)

        img_resized = self.original_image.resize((new_width, new_height), Image.LANCZOS)
        self.current_image = ImageTk.PhotoImage(img_resized)
        self.image_canvas.itemconfig(self.image_id, image=self.current_image)

        # 更新图片位置（保持对齐）
        if self.image_align == tk.W:
            x_pos = 0
        else:
            x_pos = new_width

        self.image_canvas.coords(self.image_id, (x_pos, 0))

        # 更新状态显示缩放级别
        zoom_percent = int(self.zoom_level * 100)
        self.status_label.config(text=f"{zoom_percent}%")

    def clear_preview(self):
        """清除预览"""
        self.image_canvas.itemconfig(self.image_id, image=None)
        self.current_image = None
        self.original_image = None

        # 显示提示标签
        if hasattr(self, 'drag_hint'):
            self.drag_hint.config(text="暂无图片")
            self.drag_hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

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
