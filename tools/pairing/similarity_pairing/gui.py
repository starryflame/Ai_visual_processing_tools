#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""相似度配对工具 - GUI 主界面

交互流程：
- 左右两侧都可以直接拖入图片，或一个/多个文件夹（也可以点“添加文件夹”）。
- 左侧多个文件夹可先“去重并保存”：硬线条图按 2D dHash 严格去重。
- 右侧文件夹变化后自动建立一次特征索引，之后每张左图查询不再解码右图。
- “自动配对”查看当前左图的全部达到阈值的匹配；“批量配对全部”跑完整左图。
- 导出时一对多：左图按匹配张数复制，右图逐张复制，并写出 pairs.csv 清单。
"""

import csv
import os
import queue
import shutil
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from config import (
    DARK_BG, DARK_FG, DARK_ENTRY_BG, DARK_BUTTON_BG, DARK_BUTTON_FG,
    DARK_CONTAINER_BG, DARK_HIGHLIGHT, WINDOW_WIDTH, WINDOW_HEIGHT,
    IMAGE_AREA_HEIGHT, IMAGE_AREA_WIDTH, IMAGE_EXTENSIONS,
    DEDUPE_MAX_BITS, MATCH_FLOOR, DEFAULT_MATCH_THRESHOLD, CACHE_FILE,
    FEATURE_WORKERS,
)
from similarity import FeatureCache, FeatureIndex, compute_features, dedupe_and_copy

try:
    from tkinterdnd2 import DND_FILES
    DND_AVAILABLE = True
except Exception:
    DND_AVAILABLE = False


def _fit_image(img, max_w, max_h):
    """等比缩放图片到指定区域内"""
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    if scale < 1.0:
        img = img.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS
        )
    return img


def _unique_copy_name(folder, name, used):
    """在导出目录里生成不冲突的文件名"""
    stem, ext = os.path.splitext(name)
    candidate = name
    n = 2
    while candidate.lower() in used or os.path.exists(
            os.path.join(folder, candidate)):
        candidate = f"{stem}_{n}{ext}"
        n += 1
    used.add(candidate.lower())
    return candidate


class ImagePanel:
    """单侧图片面板：多文件夹聚合、拖拽、浏览"""

    def __init__(self, parent, title, app, side, pack_side=tk.LEFT):
        self.app = app
        self.side = side
        self.on_show = None
        self.folders = []
        self.files = []
        self.current_index = 0

        frame = tk.LabelFrame(parent, text=title, padx=8, pady=8,
                              bg=DARK_BG, fg=DARK_FG)
        frame.pack(fill=tk.BOTH, expand=True, padx=4, side=pack_side)
        self.frame = frame

        header = tk.Frame(frame, bg=DARK_BG)
        header.pack(fill=tk.X, pady=(0, 6))
        tk.Button(header, text="添加文件夹", command=self.select_folder, width=10,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.RIGHT, padx=2)
        tk.Button(header, text="刷新", command=self.rebuild, width=6,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.RIGHT, padx=2)
        tk.Button(header, text="清空", command=self.clear, width=6,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.RIGHT, padx=2)
        self.summary = tk.Label(header, text="拖入图片或一个/多个文件夹",
                                bg=DARK_BG, fg="#4da6ff", anchor='w')
        self.summary.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.canvas = tk.Canvas(frame, bg=DARK_CONTAINER_BG,
                                highlightthickness=0,
                                width=IMAGE_AREA_WIDTH, height=IMAGE_AREA_HEIGHT)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=4)
        self.canvas.bind('<Configure>', self._on_canvas_resize)
        self.canvas.bind('<Double-Button-1>', lambda e: self._choose_and_show())
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW)
        self._max_w = IMAGE_AREA_WIDTH - 10
        self._max_h = IMAGE_AREA_HEIGHT - 10
        self._current_tk = None
        self._hint = tk.Label(self.canvas,
                              text="将图片 / 一个或多个文件夹拖到这里",
                              bg=DARK_CONTAINER_BG, fg="#888888")
        self._hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        bottom_row = tk.Frame(frame, bg=DARK_BG)
        bottom_row.pack(fill=tk.X, pady=(6, 0))
        tk.Button(bottom_row, text="← 上一张", command=self.prev, width=10,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom_row, text="下一张 →", command=self.nxt, width=10,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=2)
        self.status_label = tk.Label(bottom_row, text="", bg=DARK_BG,
                                     fg="#4da6ff")
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.extra = tk.Frame(frame, bg=DARK_BG)
        self.extra.pack(fill=tk.X, pady=(4, 0))

        self._register_dnd()

    # ─── 拖拽 ──────────────────────────────────────────────
    def _register_dnd(self):
        if not DND_AVAILABLE:
            return
        for widget in (self.frame, self.canvas, self._hint, self.summary):
            try:
                widget.drop_target_register(DND_FILES)
                widget.dnd_bind('<<Drop>>', self._on_drop)
            except Exception:
                pass

    def _on_drop(self, event):
        try:
            raw = self.app.root.tk.splitlist(event.data)
        except Exception:
            raw = str(event.data).split()

        folders = []
        ignored = 0
        for item in raw:
            path = os.path.normpath(str(item).strip())
            if os.path.isdir(path):
                folders.append(path)
            elif os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS:
                folders.append(os.path.dirname(path))
            else:
                ignored += 1

        if folders:
            self.add_folders(folders)
            side_name = "左侧" if self.side == 'left' else "右侧"
            self.app.set_status(
                f"{side_name}已加载 {len(self.folders)} 个文件夹，共 {len(self.files)} 张图"
            )
        if ignored:
            self.app.set_status(f"已忽略 {ignored} 个非图片项目")
        return getattr(event, 'action', None)

    # ─── 文件夹与文件列表 ──────────────────────────────────
    def select_folder(self):
        folder = filedialog.askdirectory(title="选择文件夹（可重复添加多个）")
        if folder:
            self.add_folders([folder])

    def add_folders(self, folders):
        existing = {os.path.normcase(os.path.abspath(f)) for f in self.folders}
        changed = False
        for folder in folders:
            folder = os.path.abspath(folder)
            key = os.path.normcase(folder)
            if key not in existing:
                self.folders.append(folder)
                existing.add(key)
                changed = True
        if changed:
            self.rebuild()

    def _collect_files(self):
        files = []
        seen = set()
        for folder in self.folders:
            try:
                names = sorted(os.listdir(folder))
            except OSError:
                continue
            for name in names:
                if os.path.splitext(name)[1].lower() not in IMAGE_EXTENSIONS:
                    continue
                path = os.path.join(folder, name)
                key = os.path.normcase(os.path.abspath(path))
                if key in seen:
                    continue
                seen.add(key)
                files.append(path)
        return files

    def rebuild(self):
        self.files = self._collect_files()
        self.current_index = 0
        self._update_summary()
        if self.files:
            self.show(0)
        else:
            self.clear_display()
        self.app.on_panel_files_changed(self.side)

    def set_files(self, paths, folders=None):
        """直接替换文件列表（去重完成后使用）"""
        if folders is not None:
            self.folders = list(folders)
        self.files = list(paths)
        self.current_index = 0
        self._update_summary()
        if self.files:
            self.show(0)
        else:
            self.clear_display()
        self.app.on_panel_files_changed(self.side)

    def clear(self):
        self.folders = []
        self.files = []
        self.current_index = 0
        self.clear_display()
        self._update_summary()
        self.app.on_panel_files_changed(self.side)

    def _update_summary(self):
        if not self.folders:
            self.summary.config(text="拖入图片或一个/多个文件夹")
        else:
            self.summary.config(
                text=f"{len(self.folders)} 个文件夹 · {len(self.files)} 张图"
            )

    # ─── 显示 ──────────────────────────────────────────────
    def _on_canvas_resize(self, event):
        self._max_w = max(1, event.width - 10)
        self._max_h = max(1, event.height - 10)

    def _load_display_image(self, path):
        with Image.open(path) as im:
            try:
                im.draft('RGB', (self._max_w * 2, self._max_h * 2))
            except Exception:
                pass
            im = ImageOps.exif_transpose(im)
            return _fit_image(im.convert('RGB'), self._max_w, self._max_h)

    def show(self, index):
        if not self.files or index < 0 or index >= len(self.files):
            return
        path = self.files[index]
        try:
            img = self._load_display_image(path)
            self._current_tk = ImageTk.PhotoImage(img)
            self.canvas.coords(self.image_id, 5, 5)
            self.canvas.itemconfig(self.image_id, image=self._current_tk)
            self._hint.place_forget()
            folder = os.path.basename(os.path.dirname(path))
            self.status_label.config(
                text=f"{index + 1}/{len(self.files)}  |  {folder}/{os.path.basename(path)}"
            )
            self.current_index = index
            if self.on_show:
                self.on_show(path)
        except Exception as exc:
            self.status_label.config(text=f"加载失败: {exc}")

    def show_external(self, path, status_text):
        """临时预览不在当前浏览列表里的图片（右侧匹配结果）"""
        try:
            img = self._load_display_image(path)
            self._current_tk = ImageTk.PhotoImage(img)
            self.canvas.coords(self.image_id, 5, 5)
            self.canvas.itemconfig(self.image_id, image=self._current_tk)
            self._hint.place_forget()
            self.status_label.config(text=status_text)
        except Exception as exc:
            self.status_label.config(text=f"加载失败: {exc}")

    def _choose_and_show(self):
        """双击画布也可以选择图片文件并加入所在文件夹"""
        paths = filedialog.askopenfilenames(
            title="选择图片（默认加入所在文件夹）",
            filetypes=[("图片", " ".join(f"*{e}" for e in IMAGE_EXTENSIONS))],
        )
        if paths:
            folders = sorted({os.path.dirname(os.path.abspath(p)) for p in paths})
            self.add_folders(folders)

    def prev(self):
        if self.current_index > 0:
            self.show(self.current_index - 1)

    def nxt(self):
        if self.current_index < len(self.files) - 1:
            self.show(self.current_index + 1)

    def clear_display(self):
        self.canvas.itemconfig(self.image_id, image=None)
        self._current_tk = None
        self._hint.config(text="将图片 / 一个或多个文件夹拖到这里")
        self._hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.status_label.config(text="")

    def current_path(self):
        if not self.files or self.current_index >= len(self.files):
            return None
        return self.files[self.current_index]


class GUI:
    """相似度配对工具主窗口"""

    def __init__(self, root):
        self.root = root
        self.root.title("图像相似度自动配对工具")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.config(bg=DARK_BG)

        self.export_folder = tk.StringVar()
        self.threshold_var = tk.StringVar(
            value=f"{DEFAULT_MATCH_THRESHOLD:.2f}"
        )
        self.dedupe_dir = tk.StringVar()

        self._executor = ThreadPoolExecutor(max_workers=4)
        self._ui_queue = queue.Queue()
        self._cache = FeatureCache(CACHE_FILE)

        self.index = None
        self._index_generation = 0
        self._building_index = False
        self._dedupe_running = False
        self._batch_running = False
        self._export_running = False

        self._batch_matches = None
        self._current_matches = {}
        self._match_entries = []

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_queue)
        self._update_states()

    # ─── UI 布局 ────────────────────────────────────────────
    def _build_ui(self):
        toolbar = tk.Frame(self.root, bg=DARK_BG, pady=8)
        toolbar.pack(fill=tk.X, padx=12)

        tk.Label(toolbar, text="导出目录:", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        tk.Entry(toolbar, textvariable=self.export_folder, width=22,
                 bg=DARK_ENTRY_BG, fg=DARK_FG, insertbackground=DARK_FG
                 ).pack(side=tk.LEFT, padx=3)
        tk.Button(toolbar, text="浏览", command=self._select_export, width=5,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=3)

        self.btn_auto_pair = tk.Button(toolbar, text="自动配对",
                                       command=self.auto_pair, width=10,
                                       bg="#0078d4", fg="white",
                                       font=("", 10, "bold"))
        self.btn_auto_pair.pack(side=tk.LEFT, padx=8)

        self.btn_auto_pair_all = tk.Button(toolbar, text="批量配对全部",
                                           command=self.auto_pair_all, width=12,
                                           bg="#d98e04", fg="white",
                                           font=("", 10, "bold"))
        self.btn_auto_pair_all.pack(side=tk.LEFT, padx=4)

        self.btn_export = tk.Button(toolbar, text="导出配对",
                                    command=self.export_pairs, width=10,
                                    bg="#2d7a3e", fg="white",
                                    font=("", 10, "bold"))
        self.btn_export.pack(side=tk.LEFT, padx=8)

        tk.Label(toolbar, text="相似度阈值:", bg=DARK_BG, fg=DARK_FG
                 ).pack(side=tk.LEFT, padx=(12, 0))
        self.threshold_spin = tk.Spinbox(
            toolbar, from_=0.50, to=0.99, increment=0.01, width=6,
            textvariable=self.threshold_var,
            bg=DARK_ENTRY_BG, fg=DARK_FG, insertbackground=DARK_FG,
            buttonbackground=DARK_BUTTON_BG,
        )
        self.threshold_spin.pack(side=tk.LEFT, padx=3)
        self.threshold_spin.bind("<Return>", self._on_threshold_changed)
        self.threshold_spin.bind("<FocusOut>", self._on_threshold_changed)
        self.threshold_spin.config(command=self._on_threshold_changed)

        main = tk.Frame(self.root, bg=DARK_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        self.left_panel = ImagePanel(
            main, "源图片 A（拖入图片 / 多个文件夹）", self, 'left', pack_side=tk.LEFT
        )
        self.right_panel = ImagePanel(
            main, "最佳匹配结果 B（自动建立索引）", self, 'right', pack_side=tk.LEFT
        )
        self.left_panel.on_show = self._on_left_shown

        # 左侧：去重控制
        dedupe_row = tk.Frame(self.left_panel.extra, bg=DARK_BG)
        dedupe_row.pack(fill=tk.X)
        tk.Label(dedupe_row, text="去重输出:", bg=DARK_BG, fg=DARK_FG
                 ).pack(side=tk.LEFT)
        tk.Entry(dedupe_row, textvariable=self.dedupe_dir, width=24,
                 bg=DARK_ENTRY_BG, fg=DARK_FG, insertbackground=DARK_FG
                 ).pack(side=tk.LEFT, padx=4, fill=tk.X, expand=True)
        tk.Button(dedupe_row, text="浏览", command=self._select_dedupe_dir, width=5,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT)
        self.btn_dedupe = tk.Button(dedupe_row, text="去重并保存", width=10,
                                    command=self.dedupe_left,
                                    bg="#8a5a00", fg="white",
                                    font=("", 10, "bold"))
        self.btn_dedupe.pack(side=tk.LEFT, padx=(4, 0))
        tk.Label(self.left_panel.extra,
                 text=f"硬线条图严格去重（2D dHash 汉明距离 ≤ {DEDUPE_MAX_BITS} bit）",
                 bg=DARK_BG, fg="#888888", anchor='w'
                 ).pack(fill=tk.X, pady=(2, 0))

        # 右侧：匹配列表
        tk.Label(self.right_panel.extra, text="达到阈值的匹配（点击预览）:",
                 bg=DARK_BG, fg="#4da6ff", anchor='w'
                 ).pack(fill=tk.X)
        list_row = tk.Frame(self.right_panel.extra, bg=DARK_BG)
        list_row.pack(fill=tk.X)
        self.right_match_list = tk.Listbox(
            list_row, height=4, bg=DARK_ENTRY_BG, fg=DARK_FG,
            selectbackground=DARK_HIGHLIGHT, selectforeground="white",
            activestyle='none', exportselection=False,
        )
        scrollbar = tk.Scrollbar(list_row, command=self.right_match_list.yview)
        self.right_match_list.config(yscrollcommand=scrollbar.set)
        self.right_match_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_match_list.bind('<<ListboxSelect>>', self._on_match_select)

        self._progress_var = tk.DoubleVar()
        self._progress = ttk.Progressbar(
            self.root, variable=self._progress_var, maximum=100,
            mode='determinate'
        )
        self._progress.pack(fill=tk.X, padx=12, pady=(4, 0))

        self._status = tk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W,
                                bg=DARK_ENTRY_BG, fg=DARK_FG, height=1)
        self._status.pack(fill=tk.X, padx=12, pady=(0, 8))

    # ─── 通用状态/异步 ─────────────────────────────────────
    def set_status(self, text):
        self._status.config(text=text)

    def _threshold(self):
        try:
            value = float(self.threshold_var.get())
        except ValueError:
            value = DEFAULT_MATCH_THRESHOLD
        value = min(0.99, max(0.0, value))
        self.threshold_var.set(f"{value:.2f}")
        return value

    def _update_states(self):
        has_left = bool(getattr(self.left_panel, 'files', []))
        index_ready = (
            self.index is not None
            and len(self.index) > 0
            and not self._building_index
        )
        has_matches = bool(self._batch_matches) or bool(self._current_matches)
        busy = self._batch_running or self._export_running or self._dedupe_running

        self.btn_auto_pair.config(
            state=tk.NORMAL if (index_ready and has_left and not busy)
            else tk.DISABLED
        )
        self.btn_auto_pair_all.config(
            state=tk.NORMAL if (index_ready and has_left and not busy)
            else tk.DISABLED
        )
        self.btn_export.config(
            state=tk.NORMAL if (has_matches and not busy) else tk.DISABLED
        )
        self.btn_dedupe.config(
            state=tk.NORMAL if (has_left and not busy) else tk.DISABLED
        )

    def _submit(self, work, on_done, on_error=None):
        future = self._executor.submit(work)

        def _poll():
            if not self.root.winfo_exists():
                return
            if future.done():
                try:
                    result = future.result()
                except Exception as exc:
                    if on_error:
                        on_error(exc)
                    else:
                        messagebox.showerror("错误", str(exc))
                else:
                    self._progress_var.set(100)
                    on_done(result)
            else:
                self.root.after(100, _poll)

        self.root.after(100, _poll)

    def _progress_cb(self, label):
        def callback(done, total):
            self._ui_queue.put(('progress', int(done), int(total), label))
        return callback

    def _poll_queue(self):
        try:
            while True:
                item = self._ui_queue.get_nowait()
                if item[0] == 'progress':
                    _, done, total, label = item
                    self._progress_var.set(done / max(total, 1) * 100)
                    self.set_status(f"{label} {done}/{total}")
        except queue.Empty:
            pass
        try:
            if self.root.winfo_exists():
                self.root.after(100, self._poll_queue)
        except tk.TclError:
            pass

    def _features_for(self, path):
        features = self._cache.get(path)
        if features is None:
            features = compute_features(path)
            self._cache.put(path, features)
        return features

    def _on_close(self):
        try:
            self._cache.save()
        except Exception:
            pass
        try:
            self._executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
        self.root.destroy()

    # ─── 面板变化 ──────────────────────────────────────────
    def on_panel_files_changed(self, side):
        if side == 'left':
            self._batch_matches = None
            self._current_matches.clear()
            self._match_entries = []
            if hasattr(self, 'right_match_list'):
                self.right_match_list.delete(0, tk.END)
            if not self.dedupe_dir.get() and self.left_panel.folders:
                first = self.left_panel.folders[0]
                self.dedupe_dir.set(
                    os.path.join(os.path.dirname(first),
                                 os.path.basename(first) + "_deduped")
                )
            self._update_states()
        else:
            self._start_index_build()

    # ─── 右侧索引 ──────────────────────────────────────────
    def _start_index_build(self):
        files = list(self.right_panel.files)
        self._index_generation += 1
        generation = self._index_generation
        self.index = None
        self._building_index = bool(files)
        self._update_states()

        if not files:
            self.set_status("右侧还没有图片")
            return

        self.set_status(
            f"正在为右侧 {len(files)} 张图建立特征索引（只解码一次）..."
        )

        def work():
            index = FeatureIndex(self._cache)
            index.build(files, progress_cb=self._progress_cb("建立索引"),
                        workers=FEATURE_WORKERS)
            return index

        def done(index):
            if generation != self._index_generation:
                return
            self._building_index = False
            self.index = index
            self._cache.save()
            if index.errors:
                self.set_status(
                    f"右侧索引完成: {len(index)} 张（{len(index.errors)} 张读取失败）"
                )
            else:
                self.set_status(
                    f"右侧索引已建立: {len(index)} 张，查询时不会重复解码右图"
                )
            self._update_states()

        def failed(exc):
            if generation != self._index_generation:
                return
            self._building_index = False
            self.index = None
            self.set_status(f"索引建立失败: {exc}")
            self._update_states()

        self._submit(work, done, failed)

    # ─── 配对 ──────────────────────────────────────────────
    def _matches_for(self, left_path):
        if not left_path:
            return []
        if self._batch_matches is not None and left_path in self._batch_matches:
            return self._batch_matches[left_path]
        return self._current_matches.get(left_path, [])

    def auto_pair(self):
        if self._building_index or self.index is None:
            messagebox.showwarning("提示", "右侧索引尚未就绪，请先拖入右侧图片")
            return
        left_path = self.left_panel.current_path()
        if not left_path:
            messagebox.showwarning("提示", "左侧还没有图片")
            return
        try:
            features = self._features_for(left_path)
        except Exception as exc:
            messagebox.showerror("错误", f"读取左图失败: {exc}")
            return

        matches = self.index.query(features, min_score=MATCH_FLOOR)
        self._current_matches[left_path] = matches
        if self._batch_matches is not None:
            self._batch_matches[left_path] = matches
        self._refresh_match_list(left_path)
        self._update_states()

    def auto_pair_all(self):
        if self._building_index or self.index is None:
            messagebox.showwarning("提示", "右侧索引尚未就绪，请先拖入右侧图片")
            return
        left_files = list(self.left_panel.files)
        if not left_files:
            messagebox.showwarning("提示", "左侧还没有图片")
            return

        self._batch_running = True
        self._update_states()
        index = self.index

        def work():
            total = len(left_files)
            # 左图特征解码是主要耗时，先并行提取，再统一做向量化查询
            features = {}
            with ThreadPoolExecutor(max_workers=FEATURE_WORKERS) as pool:
                futures = {
                    pool.submit(self._features_for, p): p for p in left_files
                }
                for done, future in enumerate(as_completed(futures), 1):
                    path = futures[future]
                    try:
                        features[path] = future.result()
                    except Exception:
                        features[path] = None
                    self._ui_queue.put(
                        ('progress', done, total * 2, '提取左图特征')
                    )

            results = {}
            for i, left_path in enumerate(left_files, 1):
                feat = features.get(left_path)
                results[left_path] = (
                    index.query(feat, min_score=MATCH_FLOOR)
                    if feat is not None else []
                )
                self._ui_queue.put(
                    ('progress', total + i, total * 2, '批量配对')
                )
            return results

        def done(results):
            self._batch_running = False
            self._batch_matches = results
            self._current_matches.clear()
            self._cache.save()
            threshold = self._threshold()
            hit = sum(
                1 for matches in results.values()
                if any(score >= threshold for _, score in matches)
            )
            current = self.left_panel.current_path()
            if current:
                self._refresh_match_list(current)
            self.set_status(
                f"批量配对完成: {hit}/{len(results)} 张左图有达到阈值 "
                f"{threshold:.2f} 的匹配"
            )
            self._update_states()

        def failed(exc):
            self._batch_running = False
            self.set_status(f"批量配对失败: {exc}")
            self._update_states()

        self._submit(work, done, failed)

    def _on_left_shown(self, left_path):
        if self._matches_for(left_path):
            self._refresh_match_list(left_path)
        else:
            self.right_match_list.delete(0, tk.END)
            self._match_entries = []
            if not self._batch_running:
                self.set_status("已切换左图；点击「自动配对」查看匹配")

    def _refresh_match_list(self, left_path):
        self.right_match_list.delete(0, tk.END)
        self._match_entries = []

        threshold = self._threshold()
        matches = self._matches_for(left_path)
        above = [(p, s) for p, s in matches if s >= threshold]
        for path, score in above:
            folder = os.path.basename(os.path.dirname(path))
            self.right_match_list.insert(
                tk.END,
                f"{score:.1%}  {os.path.basename(path)}  [{folder}]",
            )
            self._match_entries.append((path, score))

        if above:
            best_path, best_score = above[0]
            self.right_panel.show_external(
                best_path,
                f"最佳匹配 {best_score:.1%} | {os.path.basename(best_path)}",
            )
            self.set_status(
                f"当前左图匹配 {len(above)} 张（阈值 {threshold:.2f}），"
                f"可点击右侧列表预览"
            )
        elif matches:
            best_path, best_score = max(matches, key=lambda item: item[1])
            self.right_panel.show_external(
                best_path,
                f"最高 {best_score:.1%}（低于阈值）| {os.path.basename(best_path)}",
            )
            self.set_status(
                f"没有匹配达到阈值 {threshold:.2f}（最高 {best_score:.1%}）"
            )
        else:
            self.set_status("未找到相似图片")

    def _on_match_select(self, _event=None):
        selection = self.right_match_list.curselection()
        if not selection:
            return
        path, score = self._match_entries[selection[0]]
        self.right_panel.show_external(
            path, f"匹配度 {score:.2%} | {os.path.basename(path)}"
        )

    def _on_threshold_changed(self, _event=None):
        current = self.left_panel.current_path()
        if current and self._matches_for(current):
            self._refresh_match_list(current)
        self._update_states()

    # ─── 左侧去重 ──────────────────────────────────────────
    def _select_dedupe_dir(self):
        folder = filedialog.askdirectory(title="选择去重结果保存目录")
        if folder:
            self.dedupe_dir.set(folder)

    def dedupe_left(self):
        files = list(self.left_panel.files)
        out_dir = self.dedupe_dir.get().strip()
        if not files:
            messagebox.showwarning("提示", "左侧还没有图片")
            return
        if not out_dir:
            messagebox.showwarning("提示", "请先设置去重输出目录")
            return

        self._dedupe_running = True
        self._update_states()
        self.set_status(f"正在去重 {len(files)} 张图片...")

        def work():
            return dedupe_and_copy(
                files, out_dir, max_bits=DEDUPE_MAX_BITS,
                progress_cb=self._progress_cb("去重"),
                workers=FEATURE_WORKERS,
            )

        def done(stats):
            self._dedupe_running = False
            self._batch_matches = None
            self._current_matches.clear()
            self.right_match_list.delete(0, tk.END)
            self._match_entries = []

            self.left_panel.set_files(stats['unique_paths'], folders=[out_dir])
            message = (
                f"去重完成: {stats['total']} 张 → 唯一 {stats['unique']} 张"
                f"（移除 {stats['duplicates']} 张）"
            )
            if stats['errors']:
                message += f"，{len(stats['errors'])} 张读取失败"
            self.set_status(message)
            if stats['duplicates']:
                messagebox.showinfo(
                    "去重完成",
                    message + f"\n\n去重结果: {out_dir}"
                              f"\n重复清单: {stats['report']}",
                )
            self._update_states()

        def failed(exc):
            self._dedupe_running = False
            self.set_status(f"去重失败: {exc}")
            messagebox.showerror("去重失败", str(exc))
            self._update_states()

        self._submit(work, done, failed)

    # ─── 导出（一对多） ────────────────────────────────────
    def _select_export(self):
        folder = filedialog.askdirectory(title="选择导出目录")
        if folder:
            self.export_folder.set(folder)

    def export_pairs(self):
        export_dir = self.export_folder.get().strip()
        if not export_dir:
            messagebox.showwarning("提示", "请先选择导出目录")
            return

        data = (
            self._batch_matches
            if self._batch_matches is not None
            else self._current_matches
        )
        if not data:
            messagebox.showwarning("提示", "请先进行自动配对或批量配对")
            return

        threshold = self._threshold()
        pairs = []
        for left_path, matches in data.items():
            for right_path, score in matches:
                if score >= threshold:
                    pairs.append((left_path, right_path, score))
        if not pairs:
            messagebox.showwarning(
                "提示", f"没有相似度达到 {threshold:.2f} 的匹配可导出"
            )
            return

        counts = {}
        for left_path, _, _ in pairs:
            counts[left_path] = counts.get(left_path, 0) + 1

        rows = []
        seen = {}
        for left_path, right_path, score in pairs:
            seen[left_path] = seen.get(left_path, 0) + 1
            stem, ext = os.path.splitext(os.path.basename(left_path))
            if counts[left_path] == 1:
                left_hint = os.path.basename(left_path)
            else:
                left_hint = f"{stem}_{seen[left_path]:02d}{ext}"
            rows.append((left_path, left_hint, right_path, score))

        self._export_running = True
        self._update_states()

        def work():
            folder_a = os.path.join(export_dir, "folder_A")
            folder_b = os.path.join(export_dir, "folder_B")
            os.makedirs(folder_a, exist_ok=True)
            os.makedirs(folder_b, exist_ok=True)

            used_a = set()
            used_b = set()
            manifest_rows = []
            errors = []
            total = len(rows)

            for i, (left_src, left_hint, right_src, score) in enumerate(rows, 1):
                try:
                    left_name = _unique_copy_name(folder_a, left_hint, used_a)
                    shutil.copy2(left_src, os.path.join(folder_a, left_name))
                    right_name = _unique_copy_name(
                        folder_b, os.path.basename(right_src), used_b
                    )
                    shutil.copy2(right_src, os.path.join(folder_b, right_name))
                    manifest_rows.append((i, left_name, right_name, f"{score:.4f}"))
                except Exception as exc:
                    errors.append(f"{os.path.basename(left_src)}: {exc}")
                self._ui_queue.put(('progress', i, total, '导出'))

            manifest_path = os.path.join(export_dir, 'pairs.csv')
            with open(manifest_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(['序号', '左图', '右图', '相似度'])
                writer.writerows(manifest_rows)

            return {
                'pairs': len(manifest_rows),
                'left_images': len(counts),
                'errors': errors,
                'folder_a': folder_a,
                'folder_b': folder_b,
                'manifest': manifest_path,
            }

        def done(stats):
            self._export_running = False
            self._update_states()
            message = (
                f"导出 {stats['pairs']} 对（来自 {stats['left_images']} 张左图，"
                f"阈值 {threshold:.2f}）"
            )
            if stats['errors']:
                message += f"\n{len(stats['errors'])} 个错误"
            self.set_status(message.replace('\n', ' '))
            messagebox.showinfo(
                "导出完成",
                message + f"\n\n{stats['folder_a']}\n{stats['folder_b']}"
                          f"\n配对清单: {stats['manifest']}",
            )

        def failed(exc):
            self._export_running = False
            self.set_status(f"导出失败: {exc}")
            messagebox.showerror("导出失败", str(exc))
            self._update_states()

        self._submit(work, done, failed)
