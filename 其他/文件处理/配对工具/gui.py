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
from utils import fill_image_with_background, crop_to_square, generate_renamed_filename, get_image_files


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

        # 进度条变量
        self.progress_var = tk.DoubleVar()

        self.create_widgets()

        # 绑定键盘快捷键
        self.bind_keyboard_shortcuts()

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

        # 左图覆盖右图按钮
        tk.Button(toolbar, text="左图覆盖右图", command=self.copy_left_to_right, width=15,
                  bg="#d98e04" if self.dark_mode else "#d98e04",
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

        # 主体区域 - 三列布局
        main_frame = tk.Frame(self.root, bg=DARK_BG if self.dark_mode else None)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ========== 左列：文件列表（上下放置）==========
        list_column_frame = tk.Frame(main_frame, bg=DARK_BG if self.dark_mode else None, width=250)
        list_column_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        list_column_frame.pack_propagate(False)  # 固定宽度

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
        left_preview_frame = tk.Frame(main_frame, bg=DARK_BG if self.dark_mode else None, width=400)
        left_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 1))
        left_preview_frame.pack_propagate(False)  # 固定宽度，防止子组件影响

        # ========== 右列：右侧图片预览 ==========
        right_preview_frame = tk.Frame(main_frame, bg=DARK_BG if self.dark_mode else None, width=400)
        right_preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(1, 0))
        right_preview_frame.pack_propagate(False)  # 固定宽度，防止子组件影响

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

        # 进度条区域
        progress_frame = tk.Frame(self.root, pady=5, bg=DARK_BG if self.dark_mode else None)
        progress_frame.pack(fill=tk.X, padx=10)

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
        status_frame = tk.Frame(self.root, pady=5, bg=DARK_BG if self.dark_mode else None)
        status_frame.pack(fill=tk.X, padx=10)
        self.status_label = tk.Label(status_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W,
                                     bg=DARK_ENTRY_BG if self.dark_mode else None,
                                     fg=DARK_FG if self.dark_mode else None)
        self.status_label.pack(fill=tk.X)

    def bind_keyboard_shortcuts(self):
        """绑定键盘快捷键"""
        # 小键盘上下键：上=同步上一张，下=同步下一张
        self.root.bind_all('<KeyPress-KP_Up>', lambda e: self.sync_prev_image())
        self.root.bind_all('<KeyPress-KP_Down>', lambda e: self.sync_next_image())

        # Backspace: 同步删除（智能确认）
        self.root.bind_all('<KeyPress-BackSpace>', lambda e: self.sync_delete_images_smart())

        # 删除确认对话框引用
        self.delete_confirm_dialog = None
        self.pending_delete = None

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
        # 删除左侧图片
        if left_path and os.path.exists(left_path):
            try:
                os.remove(left_path)
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

        # 删除右侧图片
        if right_path and os.path.exists(right_path):
            try:
                os.remove(right_path)
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

        # 询问是否进行比例填充
        fill_ratio = messagebox.askyesno(
            "图片比例填充选项",
            "是否将图片统一调整为 1:1 正方形，并使用白色背景填充？\n\n是：所有图片将以白色背景填充为 1:1 正方形\n否：仅调整尺寸为两者中的较小值"
        )

        # 如果启用填充，询问是否使用裁剪模式
        crop_style = None
        if fill_ratio:
            crop_mode = messagebox.askyesno(
                "裁剪模式选项",
                "是否启用裁剪模式？\n\n是：直接裁剪为 1:1（竖图裁上面，横图裁中间）\n否：使用白色背景填充"
            )
            if crop_mode:
                crop_style = 'top'

        # 询问是否启用重命名功能
        enable_rename = messagebox.askyesno(
            "文件名重命名选项",
            "是否对导出文件进行重命名？\n\n是：按序号重命名为 pair_001.jpg, pair_002.jpg...\n否：保持原始文件名不变"
        )

        # 询问是否打乱顺序（仅在启用重命名时）
        shuffle_order = False
        if enable_rename:
            shuffle_order = messagebox.askyesno(
                "文件顺序选项",
                "是否打乱所有文件对的导出顺序？\n\n是：随机打乱序号分配，避免规律性排序\n否：按原文件名顺序依次编号"
            )

        # 确认对话框
        fill_text = "并填充为 1:1 白色背景" if fill_ratio and not crop_style else ""
        if fill_ratio and crop_style:
            fill_text = "并裁剪为 1:1（竖图裁上面，横图裁中间）"
        rename_text = "（启用序号重命名）" if enable_rename else "（使用原文件名）"
        order_text = "（已打乱顺序）" if shuffle_order else ""
        confirm_msg = f"找到 {len(common_files)} 对同名文件，是否全部导出？\n\n将调整分辨率为两者中的较小值{fill_text}{rename_text}{order_text}，并分别保存到 control 和 target 文件夹。\n(已启用多线程加速)"
        if not messagebox.askyesno("确认", confirm_msg):
            return

        # 创建导出子文件夹
        control_folder = os.path.join(export_folder, "control")
        target_folder = os.path.join(export_folder, "target")
        os.makedirs(control_folder, exist_ok=True)
        os.makedirs(target_folder, exist_ok=True)

        # 排序文件列表，如果启用打乱则随机打乱
        sorted_files = sorted(common_files)
        if shuffle_order:
            random.shuffle(sorted_files)
        total_count = len(sorted_files)

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

        # 为每个文件分配序号
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

            # 再为新文件分配剩余的序号
            remaining_indices = all_indices[len(used_indices_list):]
            for i, filename in enumerate(sorted_files):
                file_index_map[filename] = remaining_indices[i]
        else:
            # 顺序模式：从 1 开始依次分配，跳过已使用的
            next_index = 1
            for filename in sorted_files:
                while next_index in used_indices:
                    next_index += 1
                file_index_map[filename] = next_index
                next_index += 1

        # 如果启用打乱，先重命名已存在的文件
        if enable_rename and shuffle_order and existing_index_map:
            image_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
            for folder in [control_folder, target_folder]:
                # 第一步：将所有文件重命名为临时名称
                temp_map = {}  # 旧序号 -> (临时名称，新序号)
                for f in os.listdir(folder):
                    if f.startswith("pair_") and f.lower().endswith(image_extensions):
                        try:
                            old_idx = int(f[5:8])
                            if old_idx in existing_index_map:
                                new_idx = existing_index_map[old_idx]
                                ext = Path(f).suffix
                                temp_name = f"_temp_{old_idx:03d}{ext}"
                                old_path = os.path.join(folder, f)
                                temp_path = os.path.join(folder, temp_name)
                                os.rename(old_path, temp_path)
                                temp_map[old_idx] = (temp_name, new_idx)
                        except ValueError:
                            pass

                # 第二步：将临时文件重命名为最终名称
                for old_idx, (temp_name, new_idx) in temp_map.items():
                    ext = Path(temp_name).suffix
                    temp_path = os.path.join(folder, temp_name)
                    new_name = f"pair_{new_idx:03d}{ext}"
                    new_path = os.path.join(folder, new_name)
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
        paired_files = []

        def process_pair(filename):
            left_path = os.path.join(left_folder, filename)
            right_path = os.path.join(right_folder, filename)

            try:
                img_left = Image.open(left_path)
                img_right = Image.open(right_path)

                w1, h1 = img_left.size
                w2, h2 = img_right.size

                target_w = min(w1, w2)
                target_h = min(h1, h2)

                if fill_ratio:
                    target_square_size = max(target_w, target_h)
                    if crop_style:
                        # 裁剪模式：先裁剪为正方形，再调整尺寸
                        img_left_cropped = crop_to_square(img_left, crop_style)
                        img_right_cropped = crop_to_square(img_right, crop_style)
                        img_left_processed = img_left_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                        img_right_processed = img_right_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                    else:
                        # 填充模式：白色背景填充
                        img_left_processed = fill_image_with_background(img_left, (target_square_size, target_square_size))
                        img_right_processed = fill_image_with_background(img_right, (target_square_size, target_square_size))
                else:
                    img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                    img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)

                if enable_rename:
                    file_index = file_index_map[filename]
                    export_name = f"pair_{file_index:03d}{Path(filename).suffix}"
                else:
                    export_name = filename

                control_dest = os.path.join(control_folder, export_name)
                img_left_processed.save(control_dest)

                target_dest = os.path.join(target_folder, export_name)
                img_right_processed.save(target_dest)

                return (export_name, True, None)

            except Exception as e:
                return (filename, False, str(e))

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
            if fill_ratio:
                if crop_style:
                    fill_info = "（已裁剪为 1:1）"
                else:
                    fill_info = "（已填充为 1:1 白色背景）"
            else:
                fill_info = ""
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

        # 根据勾选框决定是否询问处理选项
        if self.ask_export_options.get():
            fill_ratio = messagebox.askyesno(
                "图片比例填充选项",
                "是否将图片统一调整为 1:1 正方形，并使用白色背景填充？\n\n是：所有图片将以白色背景填充为 1:1 正方形\n否：仅调整尺寸为两者中的较小值"
            )

            # 如果启用填充，询问是否使用裁剪模式
            crop_style = None
            if fill_ratio:
                crop_mode = messagebox.askyesno(
                    "裁剪模式选项",
                    "是否启用裁剪模式？\n\n是：直接裁剪为 1:1（竖图裁上面，横图裁中间）\n否：使用白色背景填充"
                )
                if crop_mode:
                    crop_style = 'top'
        else:
            # 不询问，直接原样导出
            fill_ratio = False
            crop_style = None

        control_folder = os.path.join(export_folder, "control")
        target_folder = os.path.join(export_folder, "target")
        os.makedirs(control_folder, exist_ok=True)
        os.makedirs(target_folder, exist_ok=True)

        left_name = Path(left_path).name
        right_name = Path(right_path).name
        export_name = left_name

        try:
            img_left = Image.open(left_path)
            img_right = Image.open(right_path)

            w1, h1 = img_left.size
            w2, h2 = img_right.size

            if fill_ratio:
                target_square_size = max(w1, w2, h1, h2)
                if crop_style:
                    # 裁剪模式
                    img_left_cropped = crop_to_square(img_left, crop_style)
                    img_right_cropped = crop_to_square(img_right, crop_style)
                    img_left_processed = img_left_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                    img_right_processed = img_right_cropped.resize((target_square_size, target_square_size), Image.LANCZOS)
                else:
                    # 填充模式
                    img_left_processed = fill_image_with_background(img_left, (target_square_size, target_square_size))
                    img_right_processed = fill_image_with_background(img_right, (target_square_size, target_square_size))
                final_size = f"{target_square_size}x{target_square_size}"
            else:
                target_w = min(w1, w2)
                target_h = min(h1, h2)
                img_left_processed = img_left.resize((target_w, target_h), Image.LANCZOS)
                img_right_processed = img_right.resize((target_w, target_h), Image.LANCZOS)
                final_size = f"{target_w}x{target_h}"

            control_dest = os.path.join(control_folder, export_name)
            img_left_processed.save(control_dest)

            target_dest = os.path.join(target_folder, export_name)
            img_right_processed.save(target_dest)

            if fill_ratio:
                if crop_style:
                    fill_text = "（已裁剪为 1:1）"
                else:
                    fill_text = "（已填充为 1:1 白色背景）"
            else:
                fill_text = ""
            self.status_label.config(text=f"✓ 已导出{fill_text}：{export_name} ({final_size}) | 切换图片后可再次导出")
            self.disable_export_button()

            self.left_panel.mark_as_paired(left_name)
            self.right_panel.mark_as_paired(right_name)

        except Exception as e:
            messagebox.showerror("错误", f"导出失败：{str(e)}")
            self.status_label.config(text="导出失败")
