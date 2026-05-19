#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""相似度配对工具 - GUI 主界面"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageTk

from config import (
    DARK_BG, DARK_FG, DARK_ENTRY_BG, DARK_BUTTON_BG, DARK_BUTTON_FG,
    DARK_CONTAINER_BG, DARK_HIGHLIGHT, WINDOW_WIDTH, WINDOW_HEIGHT,
    IMAGE_AREA_HEIGHT, IMAGE_AREA_WIDTH, IMAGE_EXTENSIONS
)
from similarity import compute_features, find_best_match, similarity_score


def _fit_image(img, max_w, max_h):
    """等比缩放图片到指定区域内"""
    w, h = img.size
    scale = min(max_w / w, max_h / h, 1.0)
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    return img


class ImagePanel:
    """单侧图片展示面板"""

    def __init__(self, parent, title, dark_mode=True, folder_var=None):
        self.dark_mode = dark_mode
        self.folder_path = folder_var or tk.StringVar()
        self.image_files = []
        self.current_index = 0
        self.matched_path = None
        self.match_score = 0.0

        frame = tk.LabelFrame(parent, text=title, padx=8, pady=8,
                              bg=DARK_BG, fg=DARK_FG)
        frame.pack(fill=tk.BOTH, expand=True, padx=4)

        # 文件夹选择行
        folder_row = tk.Frame(frame, bg=DARK_BG)
        folder_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(folder_row, text="文件夹:", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        tk.Entry(folder_row, textvariable=self.folder_path, width=28,
                 bg=DARK_ENTRY_BG, fg=DARK_FG, insertbackground=DARK_FG
                 ).pack(side=tk.LEFT, padx=4)
        tk.Button(folder_row, text="浏览", command=self.select_folder, width=6,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT)
        tk.Button(folder_row, text="刷新", command=self.refresh, width=6,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=4)

        # 图片展示区
        self.canvas = tk.Canvas(frame, bg=DARK_CONTAINER_BG,
                                highlightthickness=0,
                                width=IMAGE_AREA_WIDTH, height=IMAGE_AREA_HEIGHT)
        self.canvas.pack(fill=tk.BOTH, expand=True, pady=4)
        self.canvas.bind('<Configure>', self._on_canvas_resize)
        self.image_id = self.canvas.create_image(0, 0, anchor=tk.NW)
        self._max_w = IMAGE_AREA_WIDTH - 10
        self._max_h = IMAGE_AREA_HEIGHT - 10
        self._current_tk = None
        self._hint = tk.Label(self.canvas, text="请先选择文件夹",
                              bg=DARK_CONTAINER_BG, fg="#888888")
        self._hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # 底部操作行
        bottom_row = tk.Frame(frame, bg=DARK_BG)
        bottom_row.pack(fill=tk.X, pady=(6, 0))
        tk.Button(bottom_row, text="← 上一张", command=self.prev, width=10,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=2)
        tk.Button(bottom_row, text="下一张 →", command=self.nxt, width=10,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=2)
        self.status_label = tk.Label(bottom_row, text="", bg=DARK_BG,
                                     fg="#4da6ff")
        self.status_label.pack(side=tk.LEFT, padx=10)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)
            self.refresh()

    def refresh(self):
        folder = self.folder_path.get()
        if not folder or not os.path.isdir(folder):
            return
        self.image_files = sorted(
            f for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        )
        self.current_index = 0
        self.matched_path = None
        if self.image_files:
            self.show(0)
        else:
            self.clear()

    def _on_canvas_resize(self, event):
        self._max_w = event.width - 10
        self._max_h = event.height - 10

    def show(self, index):
        if not self.image_files or index < 0 or index >= len(self.image_files):
            return
        folder = self.folder_path.get()
        img_path = os.path.join(folder, self.image_files[index])
        try:
            img = Image.open(img_path)
            img = _fit_image(img, self._max_w, self._max_h)
            self._current_tk = ImageTk.PhotoImage(img)
            self.canvas.coords(self.image_id, 5, 5)
            self.canvas.itemconfig(self.image_id, image=self._current_tk)
            self._hint.place_forget()
            self.status_label.config(
                text=f"{index + 1}/{len(self.image_files)}  |  {self.image_files[index]}"
            )
            self.current_index = index
        except Exception as e:
            self.status_label.config(text=f"加载失败: {e}")

    def prev(self):
        if self.current_index > 0:
            self.show(self.current_index - 1)

    def nxt(self):
        if self.current_index < len(self.image_files) - 1:
            self.show(self.current_index + 1)

    def clear(self):
        self.canvas.itemconfig(self.image_id, image=None)
        self._current_tk = None
        self._hint.config(text="暂无图片")
        self._hint.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        self.status_label.config(text="")

    def current_path(self):
        if not self.image_files or self.current_index >= len(self.image_files):
            return None
        return os.path.join(self.folder_path.get(), self.image_files[self.current_index])


class GUI:
    """相似度配对工具主窗口"""

    def __init__(self, root):
        self.root = root
        self.root.title("图像相似度自动配对工具")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.config(bg=DARK_BG)

        self.export_folder = tk.StringVar()
        self._executor = ThreadPoolExecutor(max_workers=4)

        # 面板共享文件夹变量（toolbar 和 ImagePanel 共用同一个 StringVar）
        self.left_folder = tk.StringVar()
        self.right_folder = tk.StringVar()

        self._build_ui()

    # ─── UI 布局 ────────────────────────────────────────────
    def _build_ui(self):
        # 工具栏
        toolbar = tk.Frame(self.root, bg=DARK_BG, pady=8)
        toolbar.pack(fill=tk.X, padx=12)

        tk.Label(toolbar, text="源文件夹 A:", bg=DARK_BG, fg=DARK_FG).pack(side=tk.LEFT)
        tk.Entry(toolbar, textvariable=self.left_folder, width=25,
                 bg=DARK_ENTRY_BG, fg=DARK_FG, insertbackground=DARK_FG
                 ).pack(side=tk.LEFT, padx=3)

        tk.Label(toolbar, text="目标文件夹 B:", bg=DARK_BG, fg=DARK_FG
                 ).pack(side=tk.LEFT, padx=(16, 0))
        tk.Entry(toolbar, textvariable=self.right_folder, width=25,
                 bg=DARK_ENTRY_BG, fg=DARK_FG, insertbackground=DARK_FG
                 ).pack(side=tk.LEFT, padx=3)

        tk.Label(toolbar, text="导出目录:", bg=DARK_BG, fg=DARK_FG
                 ).pack(side=tk.LEFT, padx=(16, 0))
        tk.Entry(toolbar, textvariable=self.export_folder, width=20,
                 bg=DARK_ENTRY_BG, fg=DARK_FG, insertbackground=DARK_FG
                 ).pack(side=tk.LEFT, padx=3)
        tk.Button(toolbar, text="浏览", command=self._select_export, width=5,
                  bg=DARK_BUTTON_BG, fg=DARK_FG).pack(side=tk.LEFT, padx=3)

        self.btn_auto_pair = tk.Button(toolbar, text="自动配对",
                                       command=self.auto_pair, width=10,
                                       bg="#0078d4", fg="white", font=("", 10, "bold"))
        self.btn_auto_pair.pack(side=tk.LEFT, padx=8)

        self.btn_auto_pair_all = tk.Button(toolbar, text="批量配对全部",
                                           command=self.auto_pair_all, width=12,
                                           bg="#d98e04", fg="white", font=("", 10, "bold"))
        self.btn_auto_pair_all.pack(side=tk.LEFT, padx=4)

        self.btn_export = tk.Button(toolbar, text="导出配对",
                                    command=self.export_pairs, width=10,
                                    bg="#2d7a3e", fg="white", font=("", 10, "bold"))
        self.btn_export.pack(side=tk.LEFT, padx=8)

        # 主区域
        main = tk.Frame(self.root, bg=DARK_BG)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        self.left_panel = ImagePanel(main, "源图片 A (选一张 → 自动配对)",
                                     dark_mode=True, folder_var=self.left_folder)
        self.right_panel = ImagePanel(main, "最佳匹配结果 B",
                                      dark_mode=True, folder_var=self.right_folder)

        # 进度条
        self._progress_var = tk.DoubleVar()
        self._progress = ttk.Progressbar(
            self.root, variable=self._progress_var, maximum=100,
            mode='determinate'
        )
        self._progress.pack(fill=tk.X, padx=12, pady=(4, 0))

        # 状态栏
        self._status = tk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W,
                                bg=DARK_ENTRY_BG, fg=DARK_FG, height=1)
        self._status.pack(fill=tk.X, padx=12, pady=(0, 8))

    # ─── 导出目录 ────────────────────────────────────────────
    def _select_export(self):
        d = filedialog.askdirectory()
        if d:
            self.export_folder.set(d)

    # ─── 自动配对 ────────────────────────────────────────────
    def auto_pair(self):
        left_path = self.left_panel.current_path()
        if not left_path:
            messagebox.showwarning("提示", "请先在左侧选择一张图片")
            return
        right_folder = self.right_folder.get()
        if not right_folder or not os.path.isdir(right_folder):
            messagebox.showwarning("提示", "请先选择目标文件夹 B")
            return

        self.btn_auto_pair.config(state=tk.DISABLED)
        self._status.config(text="正在配对，请稍候...")
        self.root.update_idletasks()

        def _do():
            return find_best_match(left_path, right_folder)

        future = self._executor.submit(_do)

        def _poll():
            if future.done():
                best_path, score = future.result()
                if best_path:
                    self.right_panel.matched_path = best_path
                    self.right_panel.match_score = score
                    img = Image.open(best_path)
                    img = _fit_image(img,
                                     self.right_panel._max_w,
                                     self.right_panel._max_h)
                    self.right_panel._current_tk = ImageTk.PhotoImage(img)
                    self.right_panel.canvas.coords(self.right_panel.image_id, 5, 5)
                    self.right_panel.canvas.itemconfig(
                        self.right_panel.image_id, image=self.right_panel._current_tk)
                    self.right_panel._hint.place_forget()
                    self.right_panel.status_label.config(
                        text=f"匹配度: {score:.2%}  |  {os.path.basename(best_path)}"
                    )
                else:
                    self._status.config(text="未找到匹配图片")
                self.btn_auto_pair.config(state=tk.NORMAL)
                self._status.config(text="配对完成")
            else:
                self.root.after(100, _poll)

        self.root.after(100, _poll)

    # ─── 批量自动配对 ────────────────────────────────────────
    def auto_pair_all(self):
        """批量自动配对所有源文件夹图片（后台进度条）"""
        left_folder = self.left_folder.get()
        right_folder = self.right_folder.get()
        if not left_folder or not right_folder:
            messagebox.showwarning("提示", "请先选择两个文件夹")
            return
        if not os.path.isdir(left_folder) or not os.path.isdir(right_folder):
            messagebox.showwarning("提示", "文件夹路径无效")
            return

        left_files = sorted(
            f for f in os.listdir(left_folder)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        )
        if not left_files:
            messagebox.showinfo("提示", "源文件夹 A 中没有图片")
            return

        self.btn_auto_pair.config(state=tk.DISABLED)
        self._status.config(text=f"正在批量配对 {len(left_files)} 张图片...")
        self.root.update_idletasks()

        # 预计算右侧所有图片的特征
        right_files_map = {}
        for rf in os.listdir(right_folder):
            if os.path.splitext(rf)[1].lower() in IMAGE_EXTENSIONS:
                rp = os.path.join(right_folder, rf)
                try:
                    right_files_map[rp] = compute_features(rp)
                except Exception:
                    pass

        total = len(left_files)
        results = {}

        def _pair(fname):
            lp = os.path.join(left_folder, fname)
            try:
                left_feat = compute_features(lp)
            except Exception:
                return fname, None, 0
            best_rpath, best_score = None, -1
            for rp, rfeat in right_files_map.items():
                s = similarity_score(left_feat, rfeat)
                if s > best_score:
                    best_score = s
                    best_rpath = rp
            return fname, best_rpath, best_score

        completed = 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(_pair, f): f for f in left_files}
            for fut in as_completed(futs):
                fname, rpath, score = fut.result()
                results[fname] = (rpath, score)
                completed += 1
                self._progress_var.set(completed / total * 100)
                self._status.config(text=f"配对中 {completed}/{total}...")
                self.root.update_idletasks()

        self.left_panel._pair_results = results
        self.btn_auto_pair.config(state=tk.NORMAL)
        self._status.config(text=f"批量配对完成，共 {total} 张")

    # ─── 导出 ────────────────────────────────────────────────
    def export_pairs(self):
        export_dir = self.export_folder.get()
        if not export_dir:
            messagebox.showwarning("提示", "请先选择导出目录")
            return

        # 优先使用批量配对结果
        batch_results = getattr(self.left_panel, '_pair_results', None)
        if batch_results:
            self._export_batch(export_dir, batch_results)
            return

        # 单次配对导出
        if not self.right_panel.matched_path:
            messagebox.showwarning("提示", "请先点击「自动配对」匹配图片")
            return

        left_path = self.left_panel.current_path()
        right_path = self.right_panel.matched_path
        if not left_path:
            messagebox.showwarning("提示", "左侧没有选中图片")
            return

        base_name = Path(left_path).stem
        folder_a = os.path.join(export_dir, "folder_A")
        folder_b = os.path.join(export_dir, "folder_B")
        os.makedirs(folder_a, exist_ok=True)
        os.makedirs(folder_b, exist_ok=True)

        try:
            shutil.copy2(left_path, os.path.join(folder_a, Path(left_path).name))
            shutil.copy2(right_path, os.path.join(folder_b, Path(right_path).name))
            self._status.config(text=f"已导出: {base_name}")
            messagebox.showinfo("完成", f"已导出 1 对图片到:\n{folder_a}\n{folder_b}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")

    def _export_batch(self, export_dir, results):
        """批量导出配对结果"""
        left_folder = self.left_folder.get()
        folder_a = os.path.join(export_dir, "folder_A")
        folder_b = os.path.join(export_dir, "folder_B")
        os.makedirs(folder_a, exist_ok=True)
        os.makedirs(folder_b, exist_ok=True)

        self._progress_var.set(0)
        total = len(results)
        success = 0
        errors = []

        for i, (lname, (rpath, score)) in enumerate(results.items()):
            try:
                shutil.copy2(os.path.join(left_folder, lname),
                             os.path.join(folder_a, lname))
                if rpath and os.path.isfile(rpath):
                    shutil.copy2(rpath, os.path.join(folder_b, os.path.basename(rpath)))
                success += 1
            except Exception as e:
                errors.append(f"{lname}: {e}")
            self._progress_var.set((i + 1) / total * 100)
            self._status.config(text=f"导出中 {i + 1}/{total}...")
            self.root.update_idletasks()

        info = f"成功导出 {success}/{total} 对"
        if errors:
            info += f"\n\n{len(errors)} 个错误:" + "\n".join(errors[:5])
        self._status.config(text=info)
        messagebox.showinfo("导出完成", info + f"\n\n保存至:\n{folder_a}\n{folder_b}")
