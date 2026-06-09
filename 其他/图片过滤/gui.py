#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图片过滤工具 - GUI 主界面
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import logging
import threading
import shutil
from pathlib import Path
from urllib.parse import unquote

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

logger = logging.getLogger(__name__)

from config import (
    DARK_BG, DARK_FG, DARK_ENTRY_BG, DARK_BUTTON_BG, DARK_BUTTON_FG,
    DARK_CONTAINER_BG, DARK_HIGHLIGHT, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    RESULT_YES_BG, RESULT_NO_BG, RESULT_PENDING_BG, RESULT_MANUAL_YES_BG,
    PRESET_CONDITIONS, IMAGE_EXTENSIONS
)
from panel import ImagePreviewPanel
from ai_filter import batch_filter_images


class ImageFilterGUI:
    """图片过滤工具 GUI"""

    def __init__(self, root, config=None):
        self.root = root
        self.root.title("图片AI筛选工具")
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        self.root.minsize(900, 600)

        self.config = config
        self.dark_mode = True

        # 筛选结果数据
        self.filter_results = {}  # {filename: True/False/None}
        self.manual_overrides = {}  # {filename: "manual_yes"}  手动确认覆盖
        self.copied_files = set()  # 已复制的文件

        # 取消标志
        self._cancel_filter = False

        # 进度
        self.progress_var = tk.DoubleVar()

        self.setup_style()
        self.create_widgets()
        self.bind_shortcuts()

    def setup_style(self):
        """设置深色模式样式"""
        self.root.config(bg=DARK_BG)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background=DARK_BG)
        style.configure('TLabel', background=DARK_BG, foreground=DARK_FG)
        style.configure('TButton', background=DARK_BUTTON_BG, foreground=DARK_BUTTON_FG)
        style.configure('dark.Horizontal.TProgressbar',
                        background=DARK_HIGHLIGHT,
                        troughcolor=DARK_ENTRY_BG,
                        bordercolor=DARK_BG,
                        lightcolor=DARK_HIGHLIGHT,
                        darkcolor=DARK_HIGHLIGHT)

    def create_widgets(self):
        """创建界面组件"""
        # ── 顶部工具栏 ──
        self.toolbar = tk.Frame(self.root, bg=DARK_BG, pady=8)
        self.toolbar.pack(fill=tk.X, padx=10)

        # 第一行：文件夹选择
        row1 = tk.Frame(self.toolbar, bg=DARK_BG)
        row1.pack(fill=tk.X, pady=(0, 4))

        tk.Label(row1, text="源文件夹:", width=9, anchor=tk.W,
                 bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        self.source_folder_var = tk.StringVar()
        tk.Entry(row1, textvariable=self.source_folder_var, width=40,
                 bg=DARK_ENTRY_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(row1, text="浏览", command=self.select_source_folder, width=6,
                  bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG).pack(side=tk.LEFT)

        tk.Label(row1, text="  导出到:", width=9, anchor=tk.W,
                 bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        self.export_folder_var = tk.StringVar()
        tk.Entry(row1, textvariable=self.export_folder_var, width=30,
                 bg=DARK_ENTRY_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(row1, text="浏览", command=self.select_export_folder, width=6,
                  bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG).pack(side=tk.LEFT)

        tk.Button(row1, text="打开导出", command=self.open_export_folder, width=8,
                  bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG).pack(side=tk.RIGHT, padx=(5, 0))

        # 第二行：筛选条件
        row2 = tk.Frame(self.toolbar, bg=DARK_BG)
        row2.pack(fill=tk.X)

        tk.Label(row2, text="筛选条件:", width=9, anchor=tk.W,
                 bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        self.condition_var = tk.StringVar()
        self.condition_entry = tk.Entry(row2, textvariable=self.condition_var, width=50,
                                        bg=DARK_ENTRY_BG, fg=DARK_FG)
        self.condition_entry.pack(side=tk.LEFT, padx=(0, 5))

        # 预设条件下拉
        tk.Label(row2, text="预设:", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=(5, 2))
        self.preset_var = tk.StringVar(value="选择预设条件...")
        self.preset_combo = ttk.Combobox(
            row2, textvariable=self.preset_var,
            values=["选择预设条件..."] + PRESET_CONDITIONS,
            state="readonly", width=22
        )
        self.preset_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.preset_combo.bind('<<ComboboxSelected>>', self.on_preset_selected)

        # AI 筛选按钮
        self.filter_btn = tk.Button(row2, text="开始AI筛选", command=self.start_ai_filter,
                                     width=12, bg="#0078d4", fg="white")
        self.filter_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # 全部复制按钮
        self.copy_all_btn = tk.Button(row2, text="全部导出确认项", command=self.copy_all_matches,
                                       width=14, bg="#2d7a3e", fg="white")
        self.copy_all_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # ── 主体区域 ──
        main_frame = tk.Frame(self.root, bg=DARK_BG)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # 左侧：图片列表
        list_frame = tk.LabelFrame(main_frame, text="图片列表", padx=5, pady=5,
                                    bg=DARK_BG, fg=DARK_FG, width=280)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        list_frame.pack_propagate(False)

        # 列表筛选按钮行
        list_filter_row = tk.Frame(list_frame, bg=DARK_BG)
        list_filter_row.pack(fill=tk.X, pady=(0, 3))

        self.show_all_btn = tk.Button(list_filter_row, text="全部", command=lambda: self.refresh_listbox(),
                                       width=5, bg=DARK_HIGHLIGHT, fg="white")
        self.show_all_btn.pack(side=tk.LEFT, padx=1)

        self.show_yes_btn = tk.Button(list_filter_row, text="是", command=lambda: self.refresh_listbox("yes"),
                                       width=5, bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG)
        self.show_yes_btn.pack(side=tk.LEFT, padx=1)

        self.show_no_btn = tk.Button(list_filter_row, text="不是", command=lambda: self.refresh_listbox("no"),
                                       width=5, bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG)
        self.show_no_btn.pack(side=tk.LEFT, padx=1)

        self.show_pending_btn = tk.Button(list_filter_row, text="未判断", command=lambda: self.refresh_listbox("pending"),
                                           width=6, bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG)
        self.show_pending_btn.pack(side=tk.LEFT, padx=1)

        # 列表
        list_container = tk.Frame(list_frame, bg=DARK_BG)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.list_scrollbar = tk.Scrollbar(list_container, orient=tk.VERTICAL)
        self.list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.image_listbox = tk.Listbox(
            list_container,
            bg=DARK_ENTRY_BG, fg=DARK_FG,
            selectbackground=DARK_HIGHLIGHT, selectforeground="white",
            yscrollcommand=self.list_scrollbar.set,
            font=("Consolas", 10)
        )
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_scrollbar.config(command=self.image_listbox.yview)
        self.image_listbox.bind('<<ListboxSelect>>', self.on_list_select)

        # 拖拽文件夹导入
        if DND_AVAILABLE:
            list_frame.drop_target_register(DND_FILES)
            list_frame.dnd_bind('<<Drop>>', self.on_list_drop)
            self.list_drop_hint = tk.Label(
                list_frame, text="💡 可拖拽文件夹到此处导入",
                bg=DARK_BG, fg="#666666", font=("", 8)
            )
            self.list_drop_hint.pack(side=tk.BOTTOM, pady=(3, 0))

        # 统计标签
        self.stats_label = tk.Label(list_frame, text="", bg=DARK_BG, fg="#888888", font=("", 9))
        self.stats_label.pack(fill=tk.X, pady=(3, 0))

        # 中间：图片预览
        self.preview_panel = ImagePreviewPanel(main_frame, dark_mode=self.dark_mode)

        # ── 底部操作按钮栏 ──
        self.action_bar = tk.Frame(self.root, bg=DARK_BG, pady=6)
        self.action_bar.pack(fill=tk.X, padx=10, pady=(0, 2))

        # 导航组
        nav_group = tk.Frame(self.action_bar, bg=DARK_BG)
        nav_group.pack(side=tk.LEFT, padx=(0, 15))

        tk.Label(nav_group, text="导航", bg=DARK_BG, fg="#888888",
                 font=("", 8)).pack(anchor=tk.W, pady=(0, 2))

        nav_btns = tk.Frame(nav_group, bg=DARK_BG)
        nav_btns.pack()
        tk.Button(nav_btns, text="◀  上一张", command=self.prev_image,
                  width=11, bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(nav_btns, text="下一张  ▶", command=self.next_image,
                  width=11, bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG).pack(side=tk.LEFT)

        # 分隔
        ttk.Separator(self.action_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        # 手动操作组
        manual_group = tk.Frame(self.action_bar, bg=DARK_BG)
        manual_group.pack(side=tk.LEFT)

        tk.Label(manual_group, text="手动操作", bg=DARK_BG, fg="#888888",
                 font=("", 8)).pack(anchor=tk.W, pady=(0, 2))

        manual_btns = tk.Frame(manual_group, bg=DARK_BG)
        manual_btns.pack()
        tk.Button(manual_btns, text="✓ 手动确认复制", command=self.manual_copy,
                  width=14, bg=RESULT_MANUAL_YES_BG, fg="white",
                  font=("", 9, "bold")).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(manual_btns, text="📂 资源管理器查看", command=self.open_in_explorer,
                  width=15, bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG).pack(side=tk.LEFT)

        # ── 底部：进度条和状态栏 ──
        bottom_frame = tk.Frame(self.root, bg=DARK_BG, pady=5)
        bottom_frame.pack(fill=tk.X, padx=10)

        self.progress_bar = ttk.Progressbar(
            bottom_frame, variable=self.progress_var,
            maximum=100, mode='determinate',
            style='dark.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill=tk.X)

        self.status_label = tk.Label(
            bottom_frame, text="就绪 - 请选择源文件夹并输入筛选条件",
            relief=tk.SUNKEN, anchor=tk.W,
            bg=DARK_ENTRY_BG, fg=DARK_FG
        )
        self.status_label.pack(fill=tk.X, pady=(3, 0))

    def bind_shortcuts(self):
        """绑定键盘快捷键"""
        self.root.bind_all('<Left>', lambda e: self.prev_image())
        self.root.bind_all('<Right>', lambda e: self.next_image())
        self.root.bind_all('<Control-c>', lambda e: self.manual_copy())
        self.root.bind_all('<space>', lambda e: self.manual_copy())

    # ── 文件夹操作 ──

    def select_source_folder(self):
        folder = filedialog.askdirectory(title="选择图片源文件夹")
        if folder:
            self.source_folder_var.set(folder)
            self.preview_panel.set_folder_path(folder)
            self.preview_panel.load_folder(folder)
            self.filter_results.clear()
            self.manual_overrides.clear()
            self.copied_files.clear()
            self.refresh_listbox()
            self.update_stats()
            self.status_label.config(text=f"已加载 {len(self.preview_panel.image_files)} 张图片 | {folder}")

    def select_export_folder(self):
        folder = filedialog.askdirectory(title="选择导出目标文件夹")
        if folder:
            self.export_folder_var.set(folder)

    def open_export_folder(self):
        folder = self.export_folder_var.get()
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        else:
            messagebox.showwarning("提示", "请先选择导出文件夹")

    # ── 预设条件 ──

    def on_preset_selected(self, event=None):
        preset = self.preset_var.get()
        if preset and preset != "选择预设条件...":
            self.condition_var.set(preset)

    # ── 列表操作 ──

    def refresh_listbox(self, filter_mode="all"):
        """刷新图片列表，按筛选结果显示不同颜色

        Args:
            filter_mode: "all" | "yes" | "no" | "pending"
        """
        self.image_listbox.delete(0, tk.END)

        if not self.preview_panel.image_files:
            return

        for i, filename in enumerate(self.preview_panel.image_files):
            # 检查是否需要显示
            result = self.filter_results.get(filename)
            if filter_mode == "yes" and result is not True:
                continue
            if filter_mode == "no" and result is not False:
                continue
            if filter_mode == "pending" and result is not None:
                continue

            # 构建显示文本
            if filename in self.manual_overrides:
                prefix = "[已确认] "
            elif result is True:
                prefix = "[是]    "
            elif result is False:
                prefix = "[不是]  "
            else:
                prefix = "[...]   "

            if filename in self.copied_files:
                prefix = "[已复制] " if len(prefix) < 8 else prefix[:-1] + "✓"

            display_text = f"{prefix}{filename}"
            self.image_listbox.insert(tk.END, display_text)

            # 设置颜色
            if filename in self.manual_overrides or filename in self.copied_files:
                if filename in self.copied_files:
                    bg = RESULT_YES_BG
                else:
                    bg = RESULT_MANUAL_YES_BG
                self.image_listbox.itemconfig(tk.END, bg=bg, fg="white")
            elif result is True:
                self.image_listbox.itemconfig(tk.END, bg=RESULT_YES_BG, fg="white")
            elif result is False:
                self.image_listbox.itemconfig(tk.END, bg=RESULT_NO_BG, fg="white")
            else:
                self.image_listbox.itemconfig(tk.END, bg=RESULT_PENDING_BG, fg=DARK_FG)

        # 更新筛选按钮颜色
        btn_map = {
            "all": self.show_all_btn,
            "yes": self.show_yes_btn,
            "no": self.show_no_btn,
            "pending": self.show_pending_btn,
        }
        for mode, btn in btn_map.items():
            if mode == filter_mode:
                btn.config(bg=DARK_HIGHLIGHT, fg="white")
            else:
                btn.config(bg=DARK_BUTTON_BG, fg=DARK_BUTTON_FG)

        self.update_stats()
        self._current_filter_mode = filter_mode

    def on_list_select(self, event=None):
        """列表选择事件"""
        selection = self.image_listbox.curselection()
        if not selection:
            return

        idx = selection[0]
        text = self.image_listbox.get(idx)

        # 从显示文本中提取文件名（去除前缀）
        # 格式: "[xxx]  filename" 或 "[xxx] ✓filename"
        for prefix in ["[已复制] ✓", "[已复制] ", "[已确认] ", "[是]    ", "[不是]  ", "[...]   "]:
            if text.startswith(prefix):
                filename = text[len(prefix):]
                break
        else:
            filename = text

        # 在原列表中查找索引
        try:
            real_index = self.preview_panel.image_files.index(filename)
        except ValueError:
            return

        if real_index != self.preview_panel.current_index:
            self.preview_panel.show_image(real_index)
            self.update_result_display()

    def update_stats(self):
        """更新统计标签"""
        total = len(self.preview_panel.image_files)
        yes_count = sum(1 for v in self.filter_results.values() if v is True)
        no_count = sum(1 for v in self.filter_results.values() if v is False)
        pending = total - yes_count - no_count
        copied = len(self.copied_files)
        manual = len(self.manual_overrides)

        parts = [f"共 {total} 张"]
        if yes_count > 0:
            parts.append(f"是: {yes_count}")
        if no_count > 0:
            parts.append(f"不是: {no_count}")
        if pending > 0:
            parts.append(f"未判断: {pending}")
        if copied > 0:
            parts.append(f"已复制: {copied}")
        if manual > 0:
            parts.append(f"手动确认: {manual}")

        self.stats_label.config(text=" | ".join(parts))

    def update_result_display(self):
        """更新预览面板的 AI 结果显示"""
        filename = self.preview_panel.get_current_filename()
        if not filename:
            self.preview_panel.clear_result_display()
            return

        if filename in self.copied_files:
            self.preview_panel.set_result_display(True)
        elif filename in self.manual_overrides:
            self.preview_panel.set_result_display("manual_yes")
        else:
            result = self.filter_results.get(filename)
            self.preview_panel.set_result_display(result)

    # ── 导航 ──

    def prev_image(self):
        if self.preview_panel.prev_image():
            self._sync_listbox_selection()
            self.update_result_display()

    def next_image(self):
        if self.preview_panel.next_image():
            self._sync_listbox_selection()
            self.update_result_display()

    def _sync_listbox_selection(self):
        """同步列表框选中状态到当前图片"""
        filename = self.preview_panel.get_current_filename()
        if not filename:
            return

        # 在列表框中找到对应项
        for i in range(self.image_listbox.size()):
            text = self.image_listbox.get(i)
            if text.endswith(filename):
                self.image_listbox.selection_clear(0, tk.END)
                self.image_listbox.selection_set(i)
                self.image_listbox.activate(i)
                self.image_listbox.see(i)
                break

    # ── AI 筛选 ──

    def start_ai_filter(self):
        """启动 AI 批量筛选（识别一张、复制一张）"""
        # 验证
        source_folder = self.source_folder_var.get()
        if not source_folder or not os.path.isdir(source_folder):
            messagebox.showerror("错误", "请先选择有效的源文件夹")
            return

        condition = self.condition_var.get().strip()
        if not condition:
            messagebox.showerror("错误", "请输入筛选条件")
            return

        image_count = len(self.preview_panel.image_files)
        if image_count == 0:
            messagebox.showerror("错误", "源文件夹中没有图片文件")
            return

        # 检查导出文件夹（有则边识别边复制，无则只判断不复制）
        export_folder = self.export_folder_var.get().strip()
        if export_folder and not os.path.isdir(export_folder):
            # 文件夹不存在则自动创建
            os.makedirs(export_folder, exist_ok=True)
        will_copy = bool(export_folder and os.path.isdir(export_folder))
        copy_note = ""
        if will_copy:
            copy_note = "\n识别成功的图片将立即复制到导出文件夹"
        else:
            copy_note = "\n（未设置导出文件夹，本次只判断不复制）"

        # 确认
        confirm_msg = (
            f"即将使用 AI 对 {image_count} 张图片进行筛选\n\n"
            f"筛选条件：{condition}\n"
            f"{copy_note}\n"
            f"确认开始？"
        )
        if not messagebox.askyesno("确认", confirm_msg):
            return

        # 重置结果
        self.filter_results.clear()
        self.manual_overrides.clear()
        self.copied_files.clear()
        self.progress_var.set(0)
        self._cancel_filter = False

        # 切换按钮为取消
        self.filter_btn.config(text="取消筛选", bg="#c0392b", command=self.cancel_filter)
        self.status_label.config(text=f"AI 筛选启动中... 共 {image_count} 张")

        # 后台线程执行
        def run():
            def update_status(text):
                self.root.after(0, lambda t=text: self.status_label.config(text=t))

            def update_progress(current, total):
                pct = (current / total) * 100 if total > 0 else 0
                self.root.after(0, lambda p=pct: self.progress_var.set(p))

            def should_cancel():
                return self._cancel_filter

            def on_match(filename, image_path):
                """AI 判断为"是"时立即回调（在工作线程中调用）"""
                # 记录结果
                self.filter_results[filename] = True

                # 如果有导出文件夹，立即复制
                if will_copy:
                    dest = self._unique_path(export_folder, filename)
                    try:
                        shutil.copy2(image_path, dest)
                        self.copied_files.add(filename)
                    except Exception as e:
                        logger.error(f"即时复制失败 {filename}: {str(e)}")

                # 在主线程更新 UI
                def update_ui():
                    self.refresh_listbox()
                    # 如果当前正在预览这张图，更新结果标签
                    current = self.preview_panel.get_current_filename()
                    if current == filename:
                        self.update_result_display()
                    # 更新状态
                    total = len(self.filter_results)
                    copied = len(self.copied_files)
                    if will_copy:
                        self.status_label.config(
                            text=f"AI 筛选中... 已判断 {total} 张 | 已复制 {copied} 张"
                        )

                self.root.after(0, update_ui)

            def on_done(final_results):
                self.filter_btn.config(text="开始AI筛选", bg="#0078d4", state=tk.NORMAL,
                                       command=self.start_ai_filter)
                self.progress_var.set(100)

                if final_results and not final_results.get("_cancelled"):
                    # 更新非匹配结果（匹配的已在 on_match 中更新）
                    for item in final_results["results"]:
                        if item["filename"] not in self.filter_results:
                            self.filter_results[item["filename"]] = item["result"]

                    self.refresh_listbox()
                    self.update_result_display()

                    yes = final_results["yes_count"]
                    no = final_results["no_count"]
                    err = final_results["error_count"]
                    copied = len(self.copied_files)

                    msg = f"AI 筛选完成！满足条件: {yes} 张 | 不满足: {no} 张"
                    if copied > 0:
                        msg += f" | 已复制: {copied} 张"
                    if err > 0:
                        msg += f" | 错误: {err} 张"
                    self.status_label.config(text=msg)
                else:
                    self.status_label.config(text="AI 筛选已取消")
                    self.refresh_listbox()

            try:
                results = batch_filter_images(
                    image_folder=source_folder,
                    condition_text=condition,
                    config=self.config,
                    status_callback=update_status,
                    progress_callback=update_progress,
                    should_cancel=should_cancel,
                    on_match_callback=on_match,
                )
                self.root.after(0, lambda: on_done(results))
            except Exception as e:
                def show_error():
                    self.filter_btn.config(text="开始AI筛选", bg="#0078d4", state=tk.NORMAL,
                                           command=self.start_ai_filter)
                    self.progress_var.set(0)
                    messagebox.showerror("错误", f"AI 筛选失败：{str(e)}")
                    self.status_label.config(text=f"AI 筛选失败: {str(e)[:80]}")

                self.root.after(0, show_error)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def cancel_filter(self):
        """取消 AI 筛选"""
        self._cancel_filter = True
        self.filter_btn.config(text="正在取消...", state=tk.DISABLED)
        self.status_label.config(text="正在取消 AI 筛选，等待当前请求完成...")

    # ── 复制操作 ──

    def manual_copy(self):
        """手动确认复制当前图片（覆盖AI判断结果）"""
        export_folder = self._get_export_folder()
        if not export_folder:
            return

        filename = self.preview_panel.get_current_filename()
        image_path = self.preview_panel.get_current_image_path()
        if not filename or not image_path:
            messagebox.showwarning("提示", "没有可复制的图片")
            return

        # 标记为手动确认
        self.manual_overrides[filename] = "manual_yes"

        dest = self._unique_path(export_folder, filename)
        try:
            shutil.copy2(image_path, dest)
            self.copied_files.add(filename)
            self.refresh_listbox()
            self.update_stats()
            self.update_result_display()

            ai_result = self.filter_results.get(filename)
            ai_text = ""
            if ai_result is False:
                ai_text = '（已覆盖AI判断的「不是」）'
            elif ai_result is None:
                ai_text = "（未经过AI判断）"
            self.status_label.config(text=f"已手动确认并复制: {filename} {ai_text}")
        except Exception as e:
            messagebox.showerror("错误", f"复制失败：{str(e)}")

    def on_list_drop(self, event):
        """拖拽文件夹到列表区域，自动加载图片"""
        path = event.data

        # 清理路径格式
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        if path.startswith('file://'):
            path = path[7:]
            path = unquote(path)

        # 处理多路径（取第一个有效文件夹）
        for p in path.replace('\n', ' ').split():
            p = p.strip().strip('"')
            if os.path.isdir(p):
                self.source_folder_var.set(p)
                self.preview_panel.set_folder_path(p)
                self.preview_panel.load_folder(p)
                self.filter_results.clear()
                self.manual_overrides.clear()
                self.copied_files.clear()
                self.refresh_listbox()
                self.update_stats()
                self.status_label.config(
                    text=f"已导入 {len(self.preview_panel.image_files)} 张图片 | {p}"
                )
                return

        messagebox.showwarning("提示", "请拖拽文件夹，不是单个文件")

    def copy_all_matches(self):
        """复制所有 AI 判断为"是"和手动确认的图片"""
        export_folder = self._get_export_folder()
        if not export_folder:
            return

        source_folder = self.source_folder_var.get()

        # 收集所有需要复制的文件
        to_copy = []
        for filename in self.preview_panel.image_files:
            # 手动确认的
            if filename in self.manual_overrides:
                to_copy.append(filename)
            # AI 判断为"是"且未被手动跳过
            elif self.filter_results.get(filename) is True:
                to_copy.append(filename)

        if not to_copy:
            messagebox.showinfo("提示", "没有需要复制的图片（AI 判断为'是'或手动确认的图片）")
            return

        if not messagebox.askyesno("确认", f"即将复制 {len(to_copy)} 张图片到导出文件夹\n\n确认继续？"):
            return

        copied = 0
        errors = []
        for filename in to_copy:
            src = os.path.join(source_folder, filename)
            if not os.path.exists(src):
                errors.append(f"{filename}: 文件不存在")
                continue
            dest = self._unique_path(export_folder, filename)
            try:
                shutil.copy2(src, dest)
                self.copied_files.add(filename)
                copied += 1
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")

        self.refresh_listbox()
        self.update_stats()
        self.update_result_display()

        msg = f"成功复制 {copied}/{len(to_copy)} 张图片"
        if errors:
            msg += f"\n失败 {len(errors)} 张:\n" + "\n".join(errors[:5])
        self.status_label.config(text=msg)
        messagebox.showinfo("完成", msg)

    # ── 工具方法 ──

    def _get_export_folder(self):
        """获取并验证导出文件夹"""
        folder = self.export_folder_var.get()
        if not folder:
            # 提示选择
            folder = filedialog.askdirectory(title="选择导出目标文件夹")
            if folder:
                self.export_folder_var.set(folder)
            else:
                return None

        if not os.path.isdir(folder):
            messagebox.showerror("错误", "导出文件夹无效")
            return None

        os.makedirs(folder, exist_ok=True)
        return folder

    def _unique_path(self, folder, filename):
        """生成不重复的文件路径"""
        base = os.path.join(folder, filename)
        if not os.path.exists(base):
            return base

        name, ext = os.path.splitext(filename)
        counter = 1
        while True:
            new_path = os.path.join(folder, f"{name}_{counter}{ext}")
            if not os.path.exists(new_path):
                return new_path
            counter += 1

    def open_in_explorer(self):
        """在资源管理器中打开当前图片"""
        image_path = self.preview_panel.get_current_image_path()
        if image_path and os.path.exists(image_path):
            os.startfile(os.path.dirname(image_path))
            # 尝试选中文件
            try:
                import subprocess
                subprocess.Popen(['explorer', '/select,', image_path])
            except Exception:
                pass
        else:
            messagebox.showwarning("提示", "没有可查看的图片")
