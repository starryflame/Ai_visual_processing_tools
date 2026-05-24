#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双面板图片配对工具 - GUI 主界面
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from pathlib import Path
import shutil
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

from config import (
    DARK_BG, DARK_FG, DARK_ENTRY_BG, DARK_BUTTON_BG, DARK_BUTTON_FG,
    DARK_CONTAINER_BG, DARK_HIGHLIGHT, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
)
from panel import ImagePanel
from utils import fill_image_with_background, crop_to_square, generate_renamed_filename, get_image_files, stitch_pair_preview


class ImagePairToolGUI:
    """图片配对工具 GUI 界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("双面板图片配对工具 - 深色模式")
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")

        # 设置深色模式
        self.dark_mode = True
        self.setup_dark_mode()

        self.export_folder = tk.StringVar()
        self.export_disabled = False
        self.ask_export_options = tk.BooleanVar(value=False)  # 默认不勾选，导出时不询问处理选项
        self.preview_var = tk.BooleanVar(value=False)  # 导出时生成配对预览拼接图

        # 进度条变量
        self.progress_var = tk.DoubleVar()

        self.create_widgets()

        # 绑定键盘快捷键
        self.bind_keyboard_shortcuts()

        # 全屏模式状态
        self.is_fullscreen = False

    def setup_dark_mode(self):
        """设置深色模式"""
        if self.dark_mode:
            self.root.config(bg=DARK_BG)
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('TFrame', background=DARK_BG)
            style.configure('TLabel', background=DARK_BG, foreground=DARK_FG)
            style.configure('TButton', background=DARK_BUTTON_BG, foreground=DARK_BUTTON_FG)

    def create_widgets(self):
        """创建界面组件"""
        # 顶部工具栏
        self.toolbar = tk.Frame(self.root, pady=10, bg=DARK_BG if self.dark_mode else None)
        self.toolbar.pack(fill=tk.X, padx=10)
        toolbar = self.toolbar

        tk.Label(toolbar, text="导出文件夹:", width=12,
                 bg=DARK_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT)
        tk.Entry(toolbar, textvariable=self.export_folder, width=40,
                 bg=DARK_ENTRY_BG if self.dark_mode else None,
                 fg=DARK_FG if self.dark_mode else None).pack(side=tk.LEFT, padx=5)
        tk.Button(toolbar, text="浏览", command=self.select_export_folder, width=8,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None).pack(side=tk.LEFT)

        # 左图覆盖右图按钮
        tk.Button(toolbar, text="左图覆盖右图", command=self.copy_left_to_right, width=15,
                  bg="#d98e04" if self.dark_mode else "#d98e04",
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

        # 导出时询问选项勾选框
        self.ask_options_checkbutton = tk.Checkbutton(
            toolbar,
            text="导出时询问处理选项",
            variable=self.ask_export_options,
            bg=DARK_BG if self.dark_mode else None,
            fg=DARK_FG if self.dark_mode else None,
            activebackground=DARK_BG if self.dark_mode else None,
            activeforeground=DARK_FG if self.dark_mode else None,
            selectcolor=DARK_HIGHLIGHT  # 勾选时的背景色
        )
        self.ask_options_checkbutton.pack(side=tk.RIGHT, padx=10)

        # 导出配对预览勾选框
        self.preview_checkbutton = tk.Checkbutton(
            toolbar,
            text="生成配对预览图",
            variable=self.preview_var,
            bg=DARK_BG if self.dark_mode else None,
            fg=DARK_FG if self.dark_mode else None,
            activebackground=DARK_BG if self.dark_mode else None,
            activeforeground=DARK_FG if self.dark_mode else None,
            selectcolor=DARK_HIGHLIGHT
        )
        self.preview_checkbutton.pack(side=tk.RIGHT, padx=10)

        # 主体区域 - 三列布局
        main_frame = tk.Frame(self.root, bg=DARK_BG if self.dark_mode else None)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ========== 左列：文件列表（上下放置）==========
        self.list_column_frame = tk.Frame(main_frame, bg=DARK_BG if self.dark_mode else None, width=250)
        self.list_column_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        self.list_column_frame.pack_propagate(False)  # 固定宽度
        list_column_frame = self.list_column_frame

        # 左侧面板列表框（上半部分）
        left_list_frame = tk.LabelFrame(list_column_frame, text="左侧面板列表",
                                        padx=5, pady=5,
                                        bg=DARK_BG if self.dark_mode else None,
                                        fg=DARK_FG if self.dark_mode else None)
        left_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # 右侧面板列表框（下半部分）
        right_list_frame = tk.LabelFrame(list_column_frame, text="右侧面板列表",
                                         padx=5, pady=5,
                                         bg=DARK_BG if self.dark_mode else None,
                                         fg=DARK_FG if self.dark_mode else None)
        right_list_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 中列：左侧图片预览 ==========
        self.left_preview_frame = tk.Frame(main_frame, bg=DARK_BG if self.dark_mode else None, width=400)
        self.left_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 1))
        self.left_preview_frame.pack_propagate(False)  # 固定宽度，防止子组件影响
        left_preview_frame = self.left_preview_frame

        # ========== 右列：右侧图片预览 ==========
        self.right_preview_frame = tk.Frame(main_frame, bg=DARK_BG if self.dark_mode else None, width=400)
        self.right_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(1, 5))
        self.right_preview_frame.pack_propagate(False)  # 固定宽度，防止子组件影响
        right_preview_frame = self.right_preview_frame

        # 创建左侧面板（不带列表框，图片靠右对齐）
        self.left_panel = ImagePanel(left_preview_frame, "左侧面板 (control)",
                                     self, dark_mode=self.dark_mode, with_listbox=False,
                                     image_align=tk.E)
        # 在左列创建左侧列表框
        self.left_panel.create_listbox(left_list_frame, height=15)

        # 创建右侧面板（不带列表框，图片靠左对齐）
        self.right_panel = ImagePanel(right_preview_frame, "右侧面板 (target)",
                                      self, dark_mode=self.dark_mode, with_listbox=False,
                                      image_align=tk.W)
        # 在左列创建右侧列表框
        self.right_panel.create_listbox(right_list_frame, height=15)

        # ========== 最右列：同步操作按钮 ==========
        self.sync_column_frame = tk.Frame(main_frame, bg=DARK_BG if self.dark_mode else None, width=90)
        self.sync_column_frame.pack(side=tk.LEFT, fill=tk.Y)
        sync_column_frame = self.sync_column_frame

        self.sync_column_frame.columnconfigure(0, weight=1)
        self.sync_column_frame.rowconfigure(0, weight=1)
        self.sync_column_frame.rowconfigure(1, weight=1)
        self.sync_column_frame.rowconfigure(2, weight=1)

        tk.Button(self.sync_column_frame, text="同步上一张", command=self.sync_prev_image,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None) \
            .grid(row=0, column=0, sticky="nsew", padx=8, pady=(20, 8))

        tk.Button(self.sync_column_frame, text="同步下一张", command=self.sync_next_image,
                  bg=DARK_BUTTON_BG if self.dark_mode else None,
                  fg=DARK_BUTTON_FG if self.dark_mode else None) \
            .grid(row=1, column=0, sticky="nsew", padx=8, pady=8)

        tk.Button(self.sync_column_frame, text="同步删除", command=self.sync_delete_images,
                  bg="#d9534f" if self.dark_mode else "#d9534f",
                  fg="white") \
            .grid(row=2, column=0, sticky="nsew", padx=8, pady=(8, 20))

        # 绑定主体区域大小变化，让同步列高度始终填充
        main_frame.bind('<Configure>', lambda e: self.sync_column_frame.config(height=e.height))

        # 进度条区域
        self.progress_frame = tk.Frame(self.root, pady=5, bg=DARK_BG if self.dark_mode else None)
        self.progress_frame.pack(fill=tk.X, padx=10)
        progress_frame = self.progress_frame

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, mode='determinate',
                                            style='dark.Horizontal.TProgressbar' if self.dark_mode else 'Horizontal.TProgressbar')
        self.progress_bar.pack(fill=tk.X)

        # 配置进度条样式
        if self.dark_mode:
            style = ttk.Style()
            style.configure('dark.Horizontal.TProgressbar',
                            background=DARK_HIGHLIGHT,
                            troughcolor=DARK_ENTRY_BG,
                            bordercolor=DARK_BG,
                            lightcolor=DARK_HIGHLIGHT,
                            darkcolor=DARK_HIGHLIGHT)

        # 底部状态栏
        self.status_frame = tk.Frame(self.root, pady=5, bg=DARK_BG if self.dark_mode else None)
        self.status_frame.pack(fill=tk.X, padx=10)
        status_frame = self.status_frame
        self.status_label = tk.Label(status_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W,
                                     bg=DARK_ENTRY_BG if self.dark_mode else None,
                                     fg=DARK_FG if self.dark_mode else None)
        self.status_label.pack(fill=tk.X)

    def bind_keyboard_shortcuts(self):
        """绑定键盘快捷键"""
        # Tab: 全屏切换（override 所有控件类的默认 Tab 焦点切换）
        self._setup_tab_binding()

        # 上下键：当焦点不在图片列表时，上=同步上一张，下=同步下一张
        # 焦点在图片列表时，正常列表导航（单侧切换也会触发另一侧同步）
        self.root.bind_all('<KeyPress-Up>', lambda e: self._on_arrow_key('prev'))
        self.root.bind_all('<KeyPress-Down>', lambda e: self._on_arrow_key('next'))
        self.root.bind_all('<KeyPress-KP_Up>', lambda e: self._on_arrow_key('prev'))
        self.root.bind_all('<KeyPress-KP_Down>', lambda e: self._on_arrow_key('next'))

        # Backspace: 同步删除（智能确认）
        self.root.bind_all('<KeyPress-BackSpace>', lambda e: self.sync_delete_images_smart())

        # 删除确认对话框引用
        self.delete_confirm_dialog = None
        self.pending_delete = None

    def _on_arrow_key(self, direction):
        """处理上下箭头键：列表聚焦时放行，否则同步切换"""
        focused = self.root.focus_get()
        if focused is self.left_panel.listbox or focused is self.right_panel.listbox:
            return  # 列表聚焦时交给 Listbox 自己的导航处理
        if direction == 'prev':
            self.sync_prev_image()
        else:
            self.sync_next_image()
        return "break"

    def _setup_tab_binding(self):
        """覆盖 Tab 焦点切换，改为全屏切换"""
        # 用 Tcl 直接设置 break 来阻止默认焦点切换
        self.root.tk.call('bind', 'all', '<Tab>', 'break')

        # 全局绑定 Tab
        self.root.bind_all('<Tab>', lambda e: self.toggle_fullscreen())

        # 给所有已创建的控件绑定 Tab
        for widget in self._all_widgets():
            widget.bind('<Tab>', lambda e: self.toggle_fullscreen() or "break")

    def _all_widgets(self):
        """递归获取所有子控件"""
        widgets = []
        def collect(parent):
            for child in parent.winfo_children():
                widgets.append(child)
                collect(child)
        collect(self.root)
        return widgets

    def toggle_fullscreen(self, event=None):
        """Tab键切换全屏模式：隐藏所有组件只保留两个图片展示区域"""
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            # 进入全屏模式
            self.toolbar.pack_forget()
            self.list_column_frame.pack_forget()
            self.sync_column_frame.pack_forget()
            self.progress_frame.pack_forget()
            self.status_frame.pack_forget()

            for panel in [self.left_panel, self.right_panel]:
                panel.folder_frame.pack_forget()

            # 移除并恢复图片面板（放在最后，确保它们占满剩余空间）
            self.left_preview_frame.pack_forget()
            self.right_preview_frame.pack_forget()
            self.left_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                                         padx=5, pady=5)
            self.right_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                                          padx=5, pady=5)

            self.status_label.config(text="全屏模式 (按Tab退出)")
        else:
            # 退出全屏模式
            self.left_preview_frame.pack_forget()
            self.right_preview_frame.pack_forget()

            self.toolbar.pack(fill=tk.X, padx=10)

            main_frame = self.left_preview_frame.master
            self.list_column_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5), in_=main_frame)
            self.list_column_frame.pack_propagate(False)

            self.left_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                                         padx=(0, 1), in_=main_frame)
            self.left_preview_frame.pack_propagate(False)

            self.right_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                                          padx=(1, 5), in_=main_frame)
            self.right_preview_frame.pack_propagate(False)

            self.sync_column_frame.pack(side=tk.LEFT, fill=tk.Y, in_=main_frame)

            self.progress_frame.pack(fill=tk.X, padx=10)
            self.status_frame.pack(fill=tk.X, padx=10)

            for panel in [self.left_panel, self.right_panel]:
                panel.folder_frame.pack(fill=tk.X, pady=5, in_=panel.panel_frame)

            self.status_label.config(text="退出全屏模式")

        return "break"  # 阻止 tkinter 默认的 Tab 焦点切换行为

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

        left_info = f"左:{self.left_panel.current_index + 1}/{len(self.left_panel.image_files)}" if self.left_panel.image_files else "左：无"
        right_info = f"右:{self.right_panel.current_index + 1}/{len(self.right_panel.image_files)}" if self.right_panel.image_files else "右：无"
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

        left_info = f"左:{self.left_panel.current_index + 1}/{len(self.left_panel.image_files)}" if self.left_panel.image_files else "左：无"
        right_info = f"右:{self.right_panel.current_index + 1}/{len(self.right_panel.image_files)}" if self.right_panel.image_files else "右：无"
        self.status_label.config(text=f"✓ 同步切换完成 | {left_info} | {right_info}")

    def sync_delete_images(self):
        """同时删除左右两侧选中的图片（带确认）"""
        left_path = self.left_panel.get_current_image_path()
        right_path = self.right_panel.get_current_image_path()

        if not left_path and not right_path:
            messagebox.showwarning("警告", "两侧都没有可删除的图片")
            return

        left_name = Path(left_path).name if left_path else "无"
        right_name = Path(right_path).name if right_path else "无"

        confirm_msg = f"确定要删除以下图片吗？\n\n左侧：{left_name}\n右侧：{right_name}"
        if messagebox.askyesno("确认", confirm_msg):
            self._delete_images_internal(left_path, right_path, left_name, right_name)

    def sync_delete_images_smart(self):
        """智能删除：第一次按 Backspace 弹窗询问，询问时再按 Backspace 相当于点击'是'"""
        # 如果确认对话框正在显示，再次按 Backspace 直接确认删除
        if self.delete_confirm_dialog is not None:
            self._confirm_and_delete()
            return

        # 第一次按 Backspace，显示确认对话框
        left_path = self.left_panel.get_current_image_path()
        right_path = self.right_panel.get_current_image_path()

        if not left_path and not right_path:
            self.status_label.config(text="两侧都没有可删除的图片")
            return

        left_name = Path(left_path).name if left_path else "无"
        right_name = Path(right_path).name if right_path else "无"

        # 保存待删除信息
        self.pending_delete = (left_path, right_path, left_name, right_name)

        # 创建自定义确认对话框（非阻塞）
        self._show_delete_confirm_dialog(left_name, right_name)

    def _show_delete_confirm_dialog(self, left_name, right_name):
        """显示自定义确认对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("确认删除")
        dialog.transient(self.root)
        dialog.grab_set()

        # 对话框居中
        dialog_width = 300
        dialog_height = 150
        x = (self.root.winfo_width() - dialog_width) // 2
        y = (self.root.winfo_height() - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        dialog.resizable(False, False)

        # 消息标签
        msg = f"确定要删除以下图片吗？\n\n左侧：{left_name}\n右侧：{right_name}"
        tk.Label(dialog, text=msg, pady=20).pack()

        # 按钮框架
        btn_frame = tk.Frame(dialog)
        btn_frame.pack()

        def on_yes():
            self.delete_confirm_dialog = None
            dialog.destroy()
            if self.pending_delete:
                left_path, right_path, left_name, right_name = self.pending_delete
                self.pending_delete = None
                self._delete_images_internal(left_path, right_path, left_name, right_name)

        def on_no():
            self.delete_confirm_dialog = None
            self.pending_delete = None
            dialog.destroy()

        tk.Button(btn_frame, text="是", command=on_yes, width=10).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="否", command=on_no, width=10).pack(side=tk.LEFT, padx=10)

        # 保存对话框引用
        self.delete_confirm_dialog = dialog

        # 为对话框绑定 Backspace 事件
        dialog.bind('<KeyPress-BackSpace>', lambda e: on_yes())

    def _confirm_and_delete(self):
        """确认并执行删除"""
        if self.delete_confirm_dialog:
            self.delete_confirm_dialog.destroy()
            self.delete_confirm_dialog = None
            if self.pending_delete:
                left_path, right_path, left_name, right_name = self.pending_delete
                self.pending_delete = None
                self._delete_images_internal(left_path, right_path, left_name, right_name)

    def sync_delete_images_no_confirm(self):
        """同时删除左右两侧选中的图片（无确认，快捷键使用）"""
        left_path = self.left_panel.get_current_image_path()
        right_path = self.right_panel.get_current_image_path()

        if not left_path and not right_path:
            self.status_label.config(text="两侧都没有可删除的图片")
            return

        left_name = Path(left_path).name if left_path else "无"
        right_name = Path(right_path).name if right_path else "无"

        self._delete_images_internal(left_path, right_path, left_name, right_name)

    def _delete_images_internal(self, left_path, right_path, left_name, right_name):
        """内部删除逻辑"""
        # 删除左侧图片及同名.txt 文件
        if left_path and os.path.exists(left_path):
            try:
                os.remove(left_path)
                # 删除同名.txt 文件
                left_txt_path = Path(left_path).with_suffix('.txt')
                if left_txt_path.exists():
                    os.remove(left_txt_path)
                self.left_panel.image_files.pop(self.left_panel.current_index)
                self.left_panel.listbox.delete(self.left_panel.current_index)
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

        # 删除右侧图片及同名.txt 文件
        if right_path and os.path.exists(right_path):
            try:
                os.remove(right_path)
                # 删除同名.txt 文件
                right_txt_path = Path(right_path).with_suffix('.txt')
                if right_txt_path.exists():
                    os.remove(right_txt_path)
                self.right_panel.image_files.pop(self.right_panel.current_index)
                self.right_panel.listbox.delete(self.right_panel.current_index)
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

        left_info = f"左:{self.left_panel.current_index + 1}/{len(self.left_panel.image_files)}" if self.left_panel.image_files else "左：无"
        right_info = f"右:{self.right_panel.current_index + 1}/{len(self.right_panel.image_files)}" if self.right_panel.image_files else "右：无"
        self.status_label.config(text=f"✓ 同步删除完成 | {left_info} | {right_info}")

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
            shutil.copy2(left_path, right_path)

            self.right_panel.refresh_images()

            if right_name in self.right_panel.image_files:
                new_index = self.right_panel.image_files.index(right_name)
                self.right_panel.current_index = new_index
                self.right_panel.show_image(new_index)
                self.right_panel.listbox.selection_clear(0, tk.END)
                self.right_panel.listbox.selection_set(new_index)

            self.status_label.config(text=f"✓ 已用左图 ({left_name}) 覆盖右图 ({right_name})")

            self.enable_export_button()

        except Exception as e:
            messagebox.showerror("错误", f"覆盖失败：{str(e)}")
            self.status_label.config(text="覆盖失败")

    def _show_export_config_dialog(self):
        """弹出导出配置对话框，返回配置字典或 None（用户取消）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("导出配置")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        bg = DARK_BG if self.dark_mode else "#f0f0f0"
        fg = DARK_FG if self.dark_mode else "#000000"
        dialog.config(bg=bg)

        size_mode = tk.IntVar(value=2)   # 0=较小值, 1=裁剪, 2=填充, 3=指定分辨率
        rename_mode = tk.IntVar(value=1)  # 0=原名, 1=序号
        shuffle_var = tk.BooleanVar(value=False)
        crop_direction = tk.StringVar(value="top")
        rotate_var = tk.BooleanVar(value=False)
        custom_w_var = tk.StringVar(value="1024")
        custom_h_var = tk.StringVar(value="1024")

        body = tk.Frame(dialog, bg=bg)
        body.pack(padx=24, pady=16)

        def label(text, bold=False):
            tk.Label(body, text=text, font=("", 10, "bold") if bold else ("", 10),
                     bg=bg, fg=fg, anchor="w").pack(fill=tk.X, pady=(6, 2))

        def radio(text, var, value, **extra):
            tk.Radiobutton(body, text=text, variable=var, value=value,
                          bg=bg, fg=fg, selectcolor=bg, anchor="w",
                          **extra).pack(fill=tk.X, padx=(16, 0), pady=1)

        def checkbox(text, var):
            tk.Checkbutton(body, text=text, variable=var,
                          bg=bg, fg=fg, selectcolor=bg, anchor="w").pack(fill=tk.X, padx=(32, 0), pady=1)

        label("图片尺寸处理", bold=True)
        radio("调整为两者中较小的宽高值", size_mode, 0)
        radio("转为 1:1 正方形（裁剪：横图居中，竖图方向见下方）", size_mode, 1)
        radio("转为 1:1 正方形（白色背景填充，保留完整内容）", size_mode, 2)
        radio("统一调整为指定分辨率", size_mode, 3)

        # 自定义分辨率输入区域
        custom_size_holder = tk.Frame(body, bg=bg)
        custom_size_holder.pack(fill=tk.X)
        custom_size_row = tk.Frame(custom_size_holder, bg=bg)
        tk.Label(custom_size_row, text="目标分辨率：", bg=bg, fg=fg).pack(side=tk.LEFT)
        tk.Entry(custom_size_row, textvariable=custom_w_var, width=6,
                 bg=DARK_ENTRY_BG if self.dark_mode else "white",
                 fg=fg).pack(side=tk.LEFT)
        tk.Label(custom_size_row, text=" × ", bg=bg, fg=fg).pack(side=tk.LEFT)
        tk.Entry(custom_size_row, textvariable=custom_h_var, width=6,
                 bg=DARK_ENTRY_BG if self.dark_mode else "white",
                 fg=fg).pack(side=tk.LEFT)

        # 裁剪方向区域（占位 + 内容，初始隐藏但占布局顺序）
        crop_holder = tk.Frame(body, bg=bg)
        crop_holder.pack(fill=tk.X)
        crop_row = tk.Frame(crop_holder, bg=bg)
        tk.Label(crop_row, text="竖图裁剪方向：", bg=bg, fg=fg).pack(side=tk.LEFT)
        crop_cb = ttk.Combobox(crop_row, textvariable=crop_direction,
                               values=["上方（top）", "下方（bottom）"],
                               state="readonly", width=14)
        crop_cb.pack(side=tk.LEFT)
        crop_cb["state"] = "readonly"

        def on_mode_change(*_):
            if size_mode.get() == 1:
                crop_row.pack(fill=tk.X, padx=(32, 0), pady=1)
                custom_size_row.pack_forget()
            elif size_mode.get() == 3:
                crop_row.pack_forget()
                custom_size_row.pack(fill=tk.X, padx=(32, 0), pady=1)
            else:
                crop_row.pack_forget()
                custom_size_row.pack_forget()

        size_mode.trace_add("write", on_mode_change)

        label("文件命名方式", bold=True)
        radio("保留原始文件名（统一导出为 .png）", rename_mode, 0)
        radio("按序号重命名（pair_001.png, pair_002.png...）", rename_mode, 1)
        checkbox("随机打乱顺序", shuffle_var)

        label("数据增强", bold=True)
        checkbox("每个图片对导出4个旋转版本（0°/90°/180°/270°）", rotate_var)

        tk.Label(body, text=f"共 {self._pending_export_count} 对同名文件",
                 bg=bg, fg=DARK_HIGHLIGHT if self.dark_mode else "#0078d4",
                 font=("", 10, "bold")).pack(pady=(12, 8), anchor="w")

        btn_frame = tk.Frame(dialog, bg=bg)
        btn_frame.pack(pady=(0, 12))

        result = {"ok": False}

        def on_ok():
            result["ok"] = True
            result["fill_ratio"] = size_mode.get() >= 1
            result["size_mode"] = size_mode.get()
            if size_mode.get() == 1:
                result["crop_style"] = 'bottom' if crop_direction.get().startswith("下方") else 'top'
            else:
                result["crop_style"] = None
            if size_mode.get() == 3:
                try:
                    cw = int(custom_w_var.get())
                    ch = int(custom_h_var.get())
                    if cw <= 0 or ch <= 0:
                        raise ValueError
                    result["custom_size"] = (cw, ch)
                except ValueError:
                    messagebox.showwarning("输入错误", "请输入有效的正整数分辨率", parent=dialog)
                    return
            result["enable_rename"] = rename_mode.get() == 1
            result["shuffle_order"] = shuffle_var.get() if rename_mode.get() == 1 else False
            result["rotate"] = rotate_var.get()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        tk.Button(btn_frame, text="确定", command=on_ok, width=10).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="取消", command=on_cancel, width=10).pack(side=tk.LEFT, padx=10)

        dialog.wait_window()
        return result if result["ok"] else None

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
        left_files = set(f for f in os.listdir(left_folder)
                        if Path(f).suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp'])
        right_files = set(f for f in os.listdir(right_folder)
                         if Path(f).suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.bmp'])

        # 找出同名文件
        common_files = left_files & right_files

        if not common_files:
            messagebox.showinfo("提示", "没有找到同名文件")
            return

        from utils import crop_to_square

        # 显示导出配置对话框
        self._pending_export_count = len(common_files)
        cfg = self._show_export_config_dialog()
        if not cfg:
            return

        fill_ratio = cfg["fill_ratio"]
        crop_style = cfg["crop_style"]
        size_mode = cfg.get("size_mode", 0)
        custom_size = cfg.get("custom_size", None)
        enable_rename = cfg["enable_rename"]
        shuffle_order = cfg["shuffle_order"]
        do_rotate = cfg["rotate"]
        do_preview = self.preview_var.get()

        ROTATION_ANGLES = [0, 90, 180, 270] if do_rotate else [0]
        ROT_SUFFIX = {0: "", 90: "_r90", 180: "_r180", 270: "_r270"}

        # 创建导出子文件夹
        control_folder = os.path.join(export_folder, "control")
        target_folder = os.path.join(export_folder, "target")
        os.makedirs(control_folder, exist_ok=True)
        os.makedirs(target_folder, exist_ok=True)
        preview_folder = os.path.join(export_folder, "配对预览") if do_preview else None
        if preview_folder:
            os.makedirs(preview_folder, exist_ok=True)

        # 先展开旋转版本，再打乱
        task_list = []
        for f in sorted(common_files):
            for angle in ROTATION_ANGLES:
                task_list.append((f, angle))
        if shuffle_order:
            random.shuffle(task_list)
        total_count = len(task_list)

        # 如果启用重命名，先扫描已存在的文件，获取已使用的序号和文件
        used_indices = set()
        existing_files = []  # 已存在的文件列表
        if enable_rename:
            image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
            for folder in [control_folder, target_folder]:
                for f in os.listdir(folder):
                    if f.startswith("pair_") and f.lower().endswith(image_extensions):
                        try:
                            num = int(f[5:8])
                            used_indices.add(num)
                            existing_files.append(f)
                        except ValueError:
                            pass

        # 为每个任务分配序号
        file_index_map = {}
        existing_index_map = {}  # 已存在文件的序号映射：旧序号 -> 新序号
        if enable_rename and shuffle_order:
            # 彻底打乱模式：所有文件（已存在 + 新导出）一起分配随机序号
            total_files = len(used_indices) + total_count  # 总文件数
            all_indices = list(range(1, total_files + 1))  # 连续序号 1 到总数
            random.shuffle(all_indices)  # 打乱序号

            # 先为已存在的文件分配序号
            used_indices_list = sorted(list(used_indices))  # 排序保证一致性
            for i, old_idx in enumerate(used_indices_list):
                existing_index_map[old_idx] = all_indices[i]

            # 再为新任务分配剩余的序号
            remaining_indices = all_indices[len(used_indices_list):]
            for i, (filename, angle) in enumerate(task_list):
                file_index_map[(filename, angle)] = remaining_indices[i]
        else:
            # 顺序模式：从 1 开始依次分配，跳过已使用的
            next_index = 1
            for filename, angle in task_list:
                while next_index in used_indices:
                    next_index += 1
                file_index_map[(filename, angle)] = next_index
                next_index += 1

        # 如果启用打乱，先重命名已存在的文件（包括图片和 TXT，含旋转后缀）
        if enable_rename and shuffle_order and existing_index_map:
            image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
            for folder in [control_folder, target_folder]:
                # 第一步：将所有文件重命名为临时名称（包括 TXT）
                temp_map = {}  # 旧序号 -> [(临时名称，新序号, rotation_suffix)]
                for f in os.listdir(folder):
                    if f.startswith("pair_") and f.lower().endswith(image_extensions):
                        try:
                            old_idx = int(f[5:8])
                            if old_idx in existing_index_map:
                                new_idx = existing_index_map[old_idx]
                                ext = Path(f).suffix
                                # 提取旋转后缀（如 _r90, _r180, _r270 或无）
                                rot_part = ""
                                if len(f) > 11 and f[8] == '_':
                                    rot_part = f[8:Path(f).stem.rfind('_')] if f[8:].startswith('_r') else ""
                                    # simpler: extract everything between index and ext
                                    stem = f[:-len(ext)]  # e.g. "pair_001_r90"
                                    rot_part = stem[8:]   # e.g. "_r90" or ""
                                temp_name = f"_temp_{old_idx:03d}{rot_part}{ext}"
                                old_path = os.path.join(folder, f)
                                temp_path = os.path.join(folder, temp_name)
                                os.rename(old_path, temp_path)
                                if old_idx not in temp_map:
                                    temp_map[old_idx] = []
                                temp_map[old_idx].append((temp_name, new_idx, rot_part))
                        except ValueError:
                            pass

                # 同时处理 TXT 文件
                txt_temp_map = {}
                for f in os.listdir(folder):
                    if f.startswith("pair_") and f.lower().endswith('.txt'):
                        try:
                            old_idx = int(f[5:8])
                            if old_idx in existing_index_map:
                                new_idx = existing_index_map[old_idx]
                                stem = f[:-4]  # e.g. "pair_001" or "pair_001_r90"
                                rot_part = stem[8:] if len(stem) > 8 else ""
                                temp_name = f"_temp_{old_idx:03d}{rot_part}.txt"
                                old_path = os.path.join(folder, f)
                                temp_path = os.path.join(folder, temp_name)
                                os.rename(old_path, temp_path)
                                if old_idx not in txt_temp_map:
                                    txt_temp_map[old_idx] = []
                                txt_temp_map[old_idx].append((temp_name, new_idx, rot_part))
                        except ValueError:
                            pass

                # 第二步：将临时文件重命名为最终名称（包括 TXT）
                for old_idx, items in temp_map.items():
                    for temp_name, new_idx, rot_part in items:
                        ext = Path(temp_name).suffix
                        temp_path = os.path.join(folder, temp_name)
                        new_path = os.path.join(folder, f"pair_{new_idx:03d}{rot_part}{ext}")
                        os.rename(temp_path, new_path)

                # 重命名 TXT 文件
                for old_idx, items in txt_temp_map.items():
                    for temp_name, new_idx, rot_part in items:
                        temp_path = os.path.join(folder, temp_name)
                        new_path = os.path.join(folder, f"pair_{new_idx:03d}{rot_part}.txt")
                        os.rename(temp_path, new_path)

            self.status_label.config(text=f"已重命名已存在的文件，正在导出新文件...")
            self.root.update()

        # 重置进度条和状态
        self.progress_var.set(0)
        self.status_label.config(text=f"正在初始化线程池...")
        self.root.update()

        success_count = 0
        error_count = 0
        errors = []
        paired_files = set()

        def process_task(task):
            filename, angle = task
            left_path = os.path.join(left_folder, filename)
            right_path = os.path.join(right_folder, filename)

            try:
                img_left_raw = Image.open(left_path)
                img_right_raw = Image.open(right_path)

                w1, h1 = img_left_raw.size
                w2, h2 = img_right_raw.size

                target_w = min(w1, w2)
                target_h = min(h1, h2)

                # 旋转
                img_left = img_left_raw.rotate(angle, expand=True)
                img_right = img_right_raw.rotate(angle, expand=True)

                # 处理尺寸
                if size_mode == 3:
                    target_w, target_h = custom_size
                    img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                    img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)
                elif fill_ratio:
                    target_square_size = max(target_w, target_h)
                    if crop_style:
                        img_left_cropped = crop_to_square(img_left, crop_style)
                        img_right_cropped = crop_to_square(img_right, crop_style)
                        img_left_processed = img_left_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                        img_right_processed = img_right_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                    else:
                        img_left_processed = fill_image_with_background(img_left, (target_square_size, target_square_size))
                        img_right_processed = fill_image_with_background(img_right, (target_square_size, target_square_size))
                else:
                    img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                    img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)

                # 生成导出文件名
                suffix = ROT_SUFFIX[angle]
                if enable_rename:
                    file_index = file_index_map[(filename, angle)]
                    export_name = f"pair_{file_index:03d}{suffix}.png"
                else:
                    export_name = f"{Path(filename).stem}{suffix}.png"

                img_left_processed.save(os.path.join(control_folder, export_name))
                img_right_processed.save(os.path.join(target_folder, export_name))

                # 导出同名 TXT 标注文件
                txt_name = Path(filename).stem + '.txt'
                left_txt = os.path.join(left_folder, txt_name)
                right_txt = os.path.join(right_folder, txt_name)

                if os.path.exists(left_txt):
                    if enable_rename:
                        txt_export_name = f"pair_{file_index:03d}{suffix}.txt"
                    else:
                        txt_export_name = f"{Path(filename).stem}{suffix}.txt"
                    shutil.copy2(left_txt, os.path.join(control_folder, txt_export_name))

                if os.path.exists(right_txt):
                    if enable_rename:
                        txt_export_name = f"pair_{file_index:03d}{suffix}.txt"
                    else:
                        txt_export_name = f"{Path(filename).stem}{suffix}.txt"
                    shutil.copy2(right_txt, os.path.join(target_folder, txt_export_name))

                # 生成配对预览拼接图
                if preview_folder:
                    stitched = stitch_pair_preview(img_left_processed, img_right_processed)
                    stitched.save(os.path.join(preview_folder, export_name))

                return (filename, True, None)

            except Exception as e:
                return (filename, False, str(e))

        with ThreadPoolExecutor() as executor:
            future_to_task = {executor.submit(process_task, task): task for task in task_list}

            completed = 0
            for future in as_completed(future_to_task):
                filename, success, error_msg = future.result()
                completed += 1

                if success:
                    success_count += 1
                    paired_files.add(filename)
                else:
                    error_count += 1
                    errors.append(f"{filename}: {error_msg}")

                progress_percent = (completed / total_count) * 100
                self.progress_var.set(progress_percent)
                self.status_label.config(text=f"正在处理 {completed}/{total_count}... 成功:{success_count} 失败:{error_count}")
                self.root.update_idletasks()

        # 显示结果
        rotate_info = "（4旋转版本）" if do_rotate else ""
        if error_count == 0:
            if size_mode == 3:
                fill_info = f"（已统一调整为 {custom_size[0]}x{custom_size[1]}）"
            elif fill_ratio:
                if crop_style:
                    fill_info = "（已裁剪为 1:1）"
                else:
                    fill_info = "（已填充为 1:1 白色背景）"
            else:
                fill_info = ""
            preview_line = f"\n- {preview_folder}" if preview_folder else ""
            messagebox.showinfo("完成", f"成功导出 {success_count} 对图片！{fill_info}{rotate_info}\n所有文件保存到:\n- {control_folder}\n- {target_folder}{preview_line}")
        else:
            error_details = "\n".join(errors[:5])
            if error_count > 5:
                error_details += f"\n... 还有 {error_count - 5} 个错误"
            messagebox.showwarning("部分完成",
                                   f"成功导出 {success_count} 对图片，失败 {error_count} 对。\n{rotate_info}\n\n错误详情:\n{error_details}")

        preview_note = " | 预览图已生成" if preview_folder else ""
        self.status_label.config(text=f"✓ 自动配对完成 | 成功:{success_count} | 失败:{error_count}{preview_note}")

        for fname in paired_files:
            self.left_panel.mark_as_paired(fname)
            self.right_panel.mark_as_paired(fname)

        self.left_panel.update_listbox_colors()
        self.right_panel.update_listbox_colors()

    def export_pairs(self):
        """导出配对图片（调整分辨率后分别保存），同时导出同名 TXT 标注文件"""
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

        # 根据勾选框决定是否弹出配置对话框
        if self.ask_export_options.get():
            self._pending_export_count = 1
            cfg = self._show_export_config_dialog()
            if not cfg:
                return
            fill_ratio = cfg["fill_ratio"]
            crop_style = cfg["crop_style"]
            size_mode = cfg.get("size_mode", 0)
            custom_size = cfg.get("custom_size", None)
            do_rotate = cfg.get("rotate", False)
            do_preview = self.preview_var.get()
        else:
            fill_ratio = False
            crop_style = None
            size_mode = 0
            custom_size = None
            do_rotate = False
            do_preview = self.preview_var.get()

        control_folder = os.path.join(export_folder, "control")
        target_folder = os.path.join(export_folder, "target")
        os.makedirs(control_folder, exist_ok=True)
        os.makedirs(target_folder, exist_ok=True)

        left_name = Path(left_path).name
        right_name = Path(right_path).name
        base_name = Path(left_name).stem

        left_folder = Path(left_path).parent
        right_folder = Path(right_path).parent

        # TXT 标注文件路径
        left_txt = Path(left_folder) / (base_name + '.txt')
        right_txt = Path(right_folder) / (base_name + '.txt')

        # 分配不重复的文件名
        def alloc_name(suffix):
            name = f"{base_name}{suffix}.png"
            counter = 1
            while (os.path.exists(os.path.join(control_folder, name)) or
                   os.path.exists(os.path.join(target_folder, name))):
                name = f"{base_name}_{counter}{suffix}.png"
                counter += 1
            return name

        ROTATIONS = [0, 90, 180, 270] if do_rotate else [0]
        ROT_SUFFIX = {0: "", 90: "_r90", 180: "_r180", 270: "_r270"}
        exported = []

        try:
            img_left_raw = Image.open(left_path).copy()
            img_right_raw = Image.open(right_path).copy()

            w1, h1 = img_left_raw.size
            w2, h2 = img_right_raw.size

            for angle in ROTATIONS:
                img_left = img_left_raw.rotate(angle, expand=True)
                img_right = img_right_raw.rotate(angle, expand=True)

                lw, lh = img_left.size
                rw, rh = img_right.size

                if size_mode == 3:
                    target_w, target_h = custom_size
                    img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                    img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)
                    final_size = f"{target_w}x{target_h}"
                elif fill_ratio:
                    target_square_size = max(lw, rw, lh, rh)
                    if crop_style:
                        img_left_cropped = crop_to_square(img_left, crop_style)
                        img_right_cropped = crop_to_square(img_right, crop_style)
                        img_left_processed = img_left_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                        img_right_processed = img_right_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                    else:
                        img_left_processed = fill_image_with_background(img_left, (target_square_size, target_square_size))
                        img_right_processed = fill_image_with_background(img_right, (target_square_size, target_square_size))
                    final_size = f"{target_square_size}x{target_square_size}"
                else:
                    target_w = min(lw, rw)
                    target_h = min(lh, rh)
                    img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                    img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)
                    final_size = f"{target_w}x{target_h}"

                suffix = ROT_SUFFIX[angle]
                export_name = alloc_name(suffix)

                img_left_processed.save(os.path.join(control_folder, export_name))
                img_right_processed.save(os.path.join(target_folder, export_name))
                exported.append(export_name)

            # 导出 TXT 标注文件（每份旋转副本都复制一份）
            for export_name in exported:
                txt_export_name = Path(export_name).stem + '.txt'
                if left_txt.exists():
                    shutil.copy2(left_txt, os.path.join(control_folder, txt_export_name))
                if right_txt.exists():
                    shutil.copy2(right_txt, os.path.join(target_folder, txt_export_name))

            # 生成配对预览拼接图
            if do_preview:
                preview_folder = os.path.join(export_folder, "配对预览")
                os.makedirs(preview_folder, exist_ok=True)
                for export_name in exported:
                    ctrl_path = os.path.join(control_folder, export_name)
                    tgt_path = os.path.join(target_folder, export_name)
                    img_left = Image.open(ctrl_path)
                    img_right = Image.open(tgt_path)
                    stitched = stitch_pair_preview(img_left, img_right)
                    stitched.save(os.path.join(preview_folder, export_name))
                self.status_label.config(text=self.status_label.cget("text") + f" | 预览图已保存至 配对预览/")

            if size_mode == 3:
                fill_text = f"（已统一调整为 {custom_size[0]}x{custom_size[1]}）"
            elif fill_ratio:
                if crop_style:
                    fill_text = "（已裁剪为 1:1）"
                else:
                    fill_text = "（已填充为 1:1 白色背景）"
            else:
                fill_text = ""

            rotate_info = "（4旋转版本）" if do_rotate else ""
            self.status_label.config(text=f"✓ 已导出{fill_text}{rotate_info}：共 {len(exported)} 对 ({final_size}) | 切换图片后可再次导出")
            self.disable_export_button()

            self.left_panel.mark_as_paired(left_name)
            self.right_panel.mark_as_paired(right_name)

        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
            self.status_label.config(text="导出失败")
