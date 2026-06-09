#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片过滤工具 - 图片预览面板
"""

import tkinter as tk
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageTk

from config import (
    DARK_BG, DARK_FG, DARK_ENTRY_BG, DARK_BUTTON_BG, DARK_BUTTON_FG,
    DARK_CONTAINER_BG, DARK_HIGHLIGHT, IMAGE_AREA_HEIGHT,
    RESULT_YES_BG, RESULT_NO_BG, RESULT_PENDING_BG, RESULT_MANUAL_YES_BG
)


class ImagePreviewPanel:
    """图片预览面板，支持缩放拖拽"""

    def __init__(self, parent, dark_mode=True):
        self.parent = parent
        self.dark_mode = dark_mode
        self.image_files = []
        self.current_index = 0
        self.current_image = None

        # 缩放相关
        self.original_image = None
        self.zoom_level = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0

        # 拖拽相关
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.is_dragging = False

        self._preload_executor = ThreadPoolExecutor(max_workers=2)
        self._image_cache = {}

        self.create_widgets()

    def create_widgets(self):
        """创建面板组件"""
        bg = DARK_BG if self.dark_mode else None
        fg = DARK_FG if self.dark_mode else None

        # 主框架
        self.panel_frame = tk.Frame(self.parent, bg=bg)
        self.panel_frame.pack(fill=tk.BOTH, expand=True)

        # 图片展示画布
        self.image_canvas = tk.Canvas(
            self.panel_frame,
            bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0",
            highlightthickness=0,
            height=IMAGE_AREA_HEIGHT
        )
        self.image_canvas.pack(fill=tk.BOTH, expand=True)

        # 提示标签
        self.hint_label = tk.Label(
            self.image_canvas,
            text="请选择图片文件夹",
            bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0",
            fg="#888888",
            font=("", 14)
        )
        self.hint_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Canvas 上的图片项
        self.image_id = self.image_canvas.create_image(0, 0, anchor=tk.CENTER, image=None)

        # 绑定缩放和拖拽
        self.image_canvas.bind('<MouseWheel>', self.on_mouse_wheel)
        self.image_canvas.bind('<Button-4>', self.on_mouse_wheel)
        self.image_canvas.bind('<Button-5>', self.on_mouse_wheel)
        self.image_canvas.bind('<ButtonPress-1>', self.on_drag_start)
        self.image_canvas.bind('<B1-Motion>', self.on_drag_motion)
        self.image_canvas.bind('<ButtonRelease-1>', self.on_drag_end)

        # 底部信息栏
        self.info_frame = tk.Frame(self.panel_frame, bg=bg, height=30)
        self.info_frame.pack(fill=tk.X, pady=(3, 0))

        self.index_label = tk.Label(self.info_frame, text="", fg="#4da6ff", bg=bg, font=("", 9))
        self.index_label.pack(side=tk.LEFT, padx=5)

        self.resolution_label = tk.Label(self.info_frame, text="", fg="#888888", bg=bg, font=("", 9))
        self.resolution_label.pack(side=tk.LEFT, padx=5)

        # AI 判断结果标签
        self.result_frame = tk.Frame(self.info_frame, bg=bg)
        self.result_frame.pack(side=tk.RIGHT, padx=5)

        self.result_label = tk.Label(
            self.result_frame, text="",
            font=("", 12, "bold"),
            bg=bg, fg=DARK_FG
        )
        self.result_label.pack(side=tk.RIGHT, padx=5)

        self.result_badge = tk.Label(
            self.result_frame, text="",
            width=8, font=("", 10, "bold"),
            bg=DARK_CONTAINER_BG, fg=DARK_FG
        )
        self.result_badge.pack(side=tk.RIGHT, padx=5)

    def load_folder(self, folder_path):
        """加载文件夹中的图片"""
        from config import IMAGE_EXTENSIONS

        self.image_files = []
        if folder_path and os.path.exists(folder_path):
            for f in sorted(os.listdir(folder_path)):
                if Path(f).suffix.lower() in IMAGE_EXTENSIONS:
                    self.image_files.append(f)

        self.current_index = 0
        if self.image_files:
            self.show_image(0)
        else:
            self.clear_preview()

    def show_image(self, index):
        """显示指定索引的图片"""
        if not self.image_files or index < 0 or index >= len(self.image_files):
            self.clear_preview()
            return

        self.current_index = index

        # 检查缓存
        if index in self._image_cache:
            cached = self._image_cache.pop(index)
            self._display(cached['img'], cached['original_size'])
            self._preload_neighbors(index)
            return

        folder = self.get_image_folder()
        if not folder:
            return
        image_path = os.path.join(folder, self.image_files[index])

        def load():
            img = Image.open(image_path)
            original_size = img.size
            return {'img': img, 'original_size': original_size}

        def on_loaded(result):
            self._display(result['img'], result['original_size'])
            self._preload_neighbors(index)

        future = self._preload_executor.submit(load)

        def poll():
            if future.done():
                try:
                    on_loaded(future.result())
                except Exception as e:
                    self.hint_label.config(text=f"加载失败：{str(e)}")
                    self.hint_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            else:
                self.parent.after(30, poll)

        self.parent.after(30, poll)

    def _display(self, img, original_size):
        """在主线程中显示已加载的图片"""
        self.original_image = img
        self.zoom_level = 1.0
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # 适配 Canvas 大小
        canvas_width = max(self.image_canvas.winfo_width(), 400)
        canvas_height = max(self.image_canvas.winfo_height(), IMAGE_AREA_HEIGHT)

        target_w = canvas_width - 20
        target_h = canvas_height - 20

        scale = min(target_w / img.width, target_h / img.height, 1.0)
        if scale < 1.0:
            new_w = max(1, int(img.width * scale))
            new_h = max(1, int(img.height * scale))
            display_img = img.resize((new_w, new_h), Image.LANCZOS)
            self.zoom_level = scale
        else:
            display_img = img

        self.current_image = ImageTk.PhotoImage(display_img)

        # 居中放置
        cx = canvas_width // 2
        cy = canvas_height // 2
        self.image_canvas.coords(self.image_id, (cx, cy))
        self.image_canvas.itemconfig(self.image_id, image=self.current_image)

        self.hint_label.place_forget()

        # 更新信息
        self.index_label.config(
            text=f"当前：{self.current_index + 1}/{len(self.image_files)}"
        )
        self.resolution_label.config(text=f"分辨率：{original_size[0]}×{original_size[1]}")

    def _preload_neighbors(self, current_index):
        """预加载相邻图片"""
        if not self.image_files:
            return

        def load_and_cache(i):
            folder = self.get_image_folder()
            if not folder:
                return
            image_path = os.path.join(folder, self.image_files[i])
            img = Image.open(image_path)

            if len(self._image_cache) >= 4:
                oldest = next(iter(self._image_cache))
                del self._image_cache[oldest]

            self._image_cache[i] = {'img': img, 'original_size': img.size}

        if current_index > 0:
            self._preload_executor.submit(load_and_cache, current_index - 1)
        if current_index < len(self.image_files) - 1:
            self._preload_executor.submit(load_and_cache, current_index + 1)

    def get_image_folder(self):
        """获取图片文件夹路径（由外部设置）"""
        return getattr(self, '_folder_path', None)

    def set_folder_path(self, path):
        self._folder_path = path

    def get_current_filename(self):
        """获取当前图片文件名"""
        if not self.image_files or self.current_index >= len(self.image_files):
            return None
        return self.image_files[self.current_index]

    def get_current_image_path(self):
        """获取当前图片完整路径"""
        folder = self.get_image_folder()
        filename = self.get_current_filename()
        if folder and filename:
            return os.path.join(folder, filename)
        return None

    def set_result_display(self, result):
        """设置 AI 判断结果显示

        Args:
            result: True=是, False=不是, None=未判断/错误
        """
        if result is True:
            self.result_badge.config(text="● 是", bg=RESULT_YES_BG, fg="white")
        elif result is False:
            self.result_badge.config(text="● 不是", bg=RESULT_NO_BG, fg="white")
        elif result == "manual_yes":
            self.result_badge.config(text="● 手动确认", bg=RESULT_MANUAL_YES_BG, fg="white")
        else:
            self.result_badge.config(text="未判断", bg=RESULT_PENDING_BG, fg=DARK_FG)

    def clear_result_display(self):
        """清除结果显示"""
        self.result_badge.config(text="", bg=DARK_CONTAINER_BG if self.dark_mode else "#f0f0f0")

    def clear_preview(self):
        """清除预览"""
        self.image_canvas.itemconfig(self.image_id, image=None)
        self.current_image = None
        self.original_image = None
        self.hint_label.config(text="暂无图片")
        self.hint_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.index_label.config(text="")
        self.resolution_label.config(text="")

    def prev_image(self):
        """上一张"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image(self.current_index)
            return True
        return False

    def next_image(self):
        """下一张"""
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.show_image(self.current_index)
            return True
        return False

    # ── 缩放与拖拽 ──

    def on_mouse_wheel(self, event):
        """鼠标滚轮缩放"""
        if self.original_image is None:
            return

        if hasattr(event, 'delta'):
            delta = event.delta
        elif hasattr(event, 'num'):
            delta = 120 if event.num == 4 else -120
        else:
            return

        zoom_factor = 1.1 if delta > 0 else 0.9
        new_zoom = self.zoom_level * zoom_factor

        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return

        mouse_x = event.x
        mouse_y = event.y
        old_zoom = self.zoom_level
        self.zoom_level = new_zoom

        new_w = int(self.original_image.width * self.zoom_level)
        new_h = int(self.original_image.height * self.zoom_level)

        img_resized = self.original_image.resize((new_w, new_h), Image.LANCZOS)
        self.current_image = ImageTk.PhotoImage(img_resized)
        self.image_canvas.itemconfig(self.image_id, image=self.current_image)

        # 以鼠标位置为中心缩放
        cx = self.image_canvas.winfo_width() // 2
        cy = self.image_canvas.winfo_height() // 2

        old_img_x = mouse_x - (cx + self.drag_offset_x)
        new_img_x = old_img_x * (new_zoom / old_zoom)
        new_x = mouse_x - new_img_x

        old_img_y = mouse_y - (cy + self.drag_offset_y)
        new_img_y = old_img_y * (new_zoom / old_zoom)
        new_y = mouse_y - new_img_y

        self.image_canvas.coords(self.image_id, (new_x, new_y))
        self.drag_offset_x = new_x - cx
        self.drag_offset_y = new_y - cy

        zoom_pct = int(self.zoom_level * 100)
        self.resolution_label.config(text=f"{zoom_pct}%")

    def on_drag_start(self, event):
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag_motion(self, event):
        if not self.is_dragging:
            return
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        self.image_canvas.move(self.image_id, dx, dy)
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.drag_offset_x += dx
        self.drag_offset_y += dy

    def on_drag_end(self, event):
        self.is_dragging = False
