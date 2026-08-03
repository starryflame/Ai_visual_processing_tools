#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF 转图片工具
支持单个 PDF 或批量文件夹扫描，加密 PDF 自动弹窗输入密码
"""

import sys
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# ---- 依赖检查 ----
MISSING_DEPS = []
try:
    import fitz  # PyMuPDF
except ImportError:
    MISSING_DEPS.append("PyMuPDF (pip install PyMuPDF)")
try:
    from PIL import Image
except ImportError:
    MISSING_DEPS.append("Pillow (pip install Pillow)")


# ---------------- 配色主题 ----------------
class Theme:
    BG_ROOT      = "#e8f4fd"
    BG_MAIN      = "#f0f7fc"
    BG_CARD      = "#ffffff"
    ACCENT       = "#2196F3"
    ACCENT_DEEP  = "#1565C0"
    TEXT_TITLE   = "#0d2137"
    TEXT_BODY    = "#37474f"
    TEXT_HINT    = "#90a4ae"
    TEXT_WHITE   = "#ffffff"
    BORDER       = "#dbe8f0"
    SUCCESS      = "#4CAF50"
    WARNING      = "#FF9800"
    ERROR        = "#F44336"


# ---------------- 主界面 ----------------
class PDFToImageApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF 转图片工具")
        self.root.geometry("680x520")
        self.root.minsize(560, 420)
        self.root.configure(bg=Theme.BG_ROOT)

        self.input_mode = tk.StringVar(value="file")   # "file" or "folder"
        self.source_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.format_var = tk.StringVar(value="PNG")
        self.dpi_var = tk.IntVar(value=200)
        self.quality_var = tk.IntVar(value=95)
        self._converting = False

        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        # 标题栏
        header = tk.Frame(self.root, bg=Theme.BG_CARD, height=56)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        tk.Label(
            header, text="📄 PDF 转图片工具",
            font=("Microsoft YaHei", 16, "bold"),
            bg=Theme.BG_CARD, fg=Theme.TEXT_TITLE
        ).pack(side=tk.LEFT, padx=24, pady=12)

        # 主区域
        main = tk.Frame(self.root, bg=Theme.BG_MAIN)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=12)

        # ---- 输入模式 ----
        mode_frame = tk.LabelFrame(main, text="输入模式", font=("Microsoft YaHei", 10, "bold"),
                                   bg=Theme.BG_CARD, fg=Theme.TEXT_BODY,
                                   padx=14, pady=10)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        mode_inner = tk.Frame(mode_frame, bg=Theme.BG_CARD)
        mode_inner.pack()

        tk.Radiobutton(mode_inner, text="单个 PDF 文件", variable=self.input_mode,
                       value="file", font=("Microsoft YaHei", 10),
                       bg=Theme.BG_CARD, activebackground=Theme.BG_CARD,
                       command=self._on_mode_change).pack(side=tk.LEFT, padx=(0, 20))
        tk.Radiobutton(mode_inner, text="扫描文件夹内所有 PDF", variable=self.input_mode,
                       value="folder", font=("Microsoft YaHei", 10),
                       bg=Theme.BG_CARD, activebackground=Theme.BG_CARD,
                       command=self._on_mode_change).pack(side=tk.LEFT)

        # ---- 来源选择 ----
        src_frame = tk.LabelFrame(main, text="来源", font=("Microsoft YaHei", 10, "bold"),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_BODY,
                                  padx=14, pady=10)
        src_frame.pack(fill=tk.X, pady=(0, 10))

        src_inner = tk.Frame(src_frame, bg=Theme.BG_CARD)
        src_inner.pack(fill=tk.X)

        self.src_entry = tk.Entry(src_inner, textvariable=self.source_path,
                                  font=("Microsoft YaHei", 10), state="readonly",
                                  readonlybackground=Theme.BG_MAIN, relief=tk.FLAT)
        self.src_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        self.browse_btn = tk.Button(src_inner, text="浏览...", command=self._browse_source,
                                    font=("Microsoft YaHei", 9),
                                    bg=Theme.ACCENT, fg=Theme.TEXT_WHITE,
                                    relief=tk.FLAT, cursor="hand2", bd=0, padx=14, pady=4,
                                    activebackground=Theme.ACCENT_DEEP,
                                    activeforeground=Theme.TEXT_WHITE)
        self.browse_btn.pack(side=tk.RIGHT)

        # ---- 输出目录 ----
        out_frame = tk.LabelFrame(main, text="输出目录", font=("Microsoft YaHei", 10, "bold"),
                                  bg=Theme.BG_CARD, fg=Theme.TEXT_BODY,
                                  padx=14, pady=10)
        out_frame.pack(fill=tk.X, pady=(0, 10))

        out_inner = tk.Frame(out_frame, bg=Theme.BG_CARD)
        out_inner.pack(fill=tk.X)

        self.out_entry = tk.Entry(out_inner, textvariable=self.output_dir,
                                  font=("Microsoft YaHei", 10),
                                  bg=Theme.BG_MAIN, relief=tk.FLAT)
        self.out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 8))

        tk.Button(out_inner, text="浏览...", command=self._browse_output,
                  font=("Microsoft YaHei", 9),
                  bg=Theme.ACCENT, fg=Theme.TEXT_WHITE,
                  relief=tk.FLAT, cursor="hand2", bd=0, padx=14, pady=4,
                  activebackground=Theme.ACCENT_DEEP,
                  activeforeground=Theme.TEXT_WHITE).pack(side=tk.RIGHT)

        # ---- 参数 ----
        param_frame = tk.LabelFrame(main, text="输出参数", font=("Microsoft YaHei", 10, "bold"),
                                    bg=Theme.BG_CARD, fg=Theme.TEXT_BODY,
                                    padx=14, pady=10)
        param_frame.pack(fill=tk.X, pady=(0, 10))

        param_inner = tk.Frame(param_frame, bg=Theme.BG_CARD)
        param_inner.pack()

        # 格式
        tk.Label(param_inner, text="格式:", font=("Microsoft YaHei", 10),
                 bg=Theme.BG_CARD, fg=Theme.TEXT_BODY).pack(side=tk.LEFT)
        fmt_combo = ttk.Combobox(param_inner, textvariable=self.format_var,
                                 values=["PNG", "JPG", "WEBP", "BMP"],
                                 state="readonly", width=8, font=("Microsoft YaHei", 10))
        fmt_combo.pack(side=tk.LEFT, padx=(4, 18))

        # DPI
        tk.Label(param_inner, text="DPI:", font=("Microsoft YaHei", 10),
                 bg=Theme.BG_CARD, fg=Theme.TEXT_BODY).pack(side=tk.LEFT)
        dpi_spin = ttk.Spinbox(param_inner, from_=72, to=600, textvariable=self.dpi_var,
                               width=6, font=("Microsoft YaHei", 10))
        dpi_spin.pack(side=tk.LEFT, padx=(4, 18))

        # JPEG 质量
        tk.Label(param_inner, text="JPG质量:", font=("Microsoft YaHei", 10),
                 bg=Theme.BG_CARD, fg=Theme.TEXT_BODY).pack(side=tk.LEFT)
        q_spin = ttk.Spinbox(param_inner, from_=10, to=100, textvariable=self.quality_var,
                             width=6, font=("Microsoft YaHei", 10))
        q_spin.pack(side=tk.LEFT, padx=(4, 0))

        # ---- 进度与操作 ----
        action_frame = tk.Frame(main, bg=Theme.BG_MAIN)
        action_frame.pack(fill=tk.X, pady=(4, 0))

        self.convert_btn = tk.Button(action_frame, text="开始转换", command=self._start_conversion,
                                     font=("Microsoft YaHei", 11, "bold"),
                                     bg=Theme.ACCENT, fg=Theme.TEXT_WHITE,
                                     relief=tk.FLAT, cursor="hand2", bd=0, padx=24, pady=6,
                                     activebackground=Theme.ACCENT_DEEP,
                                     activeforeground=Theme.TEXT_WHITE)
        self.convert_btn.pack(side=tk.LEFT)

        self.stop_btn = tk.Button(action_frame, text="停止", command=self._stop_conversion,
                                  font=("Microsoft YaHei", 10),
                                  bg=Theme.WARNING, fg=Theme.TEXT_WHITE,
                                  relief=tk.FLAT, cursor="hand2", bd=0, padx=16, pady=6,
                                  state=tk.DISABLED,
                                  activebackground="#E68900",
                                  activeforeground=Theme.TEXT_WHITE)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 进度条
        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(12, 4))

        # 状态文字
        self.status_label = tk.Label(main, text="就绪", font=("Microsoft YaHei", 9),
                                     bg=Theme.BG_MAIN, fg=Theme.TEXT_HINT, anchor="w")
        self.status_label.pack(fill=tk.X)

    # ---------- 浏览 ----------
    def _on_mode_change(self):
        self.source_path.set("")

    def _browse_source(self):
        if self.input_mode.get() == "file":
            path = filedialog.askopenfilename(
                title="选择 PDF 文件",
                filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")]
            )
        else:
            path = filedialog.askdirectory(title="选择包含 PDF 的文件夹")
        if path:
            self.source_path.set(path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_dir.set(path)

    # ---------- 转换逻辑 ----------
    def _start_conversion(self):
        src = self.source_path.get().strip()
        out = self.output_dir.get().strip()

        if not src:
            messagebox.showwarning("提示", "请先选择来源 PDF 文件或文件夹")
            return
        if not out:
            messagebox.showwarning("提示", "请先选择输出目录")
            return
        if not os.path.exists(src):
            messagebox.showerror("错误", f"来源路径不存在:\n{src}")
            return

        if self.input_mode.get() == "file":
            if not src.lower().endswith(".pdf"):
                messagebox.showwarning("提示", "请选择 .pdf 文件")
                return
            pdf_files = [src]
        else:
            pdf_files = sorted([
                os.path.join(src, f) for f in os.listdir(src)
                if f.lower().endswith(".pdf")
            ])
            if not pdf_files:
                messagebox.showinfo("提示", "该文件夹中没有找到 PDF 文件")
                return

        os.makedirs(out, exist_ok=True)

        self._converting = True
        self.convert_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.progress["value"] = 0
        self.status_label.configure(text="正在扫描 PDF 页数...", fg=Theme.TEXT_BODY)

        threading.Thread(target=self._convert_pdfs, args=(pdf_files, out), daemon=True).start()

    def _stop_conversion(self):
        self._converting = False
        self.status_label.configure(text="用户停止", fg=Theme.WARNING)

    def _convert_pdfs(self, pdf_files, out_dir):
        fmt = self.format_var.get().lower()
        dpi = self.dpi_var.get()
        quality = self.quality_var.get()
        total_pages = 0
        done_pages = 0

        # 先统计总页数
        pdf_pages_list = []
        for pdf_path in pdf_files:
            if not self._converting:
                self._finish_ui()
                return
            try:
                doc = fitz.open(pdf_path)
                if doc.needs_pass:
                    pw = self._ask_password(os.path.basename(pdf_path))
                    if pw is None:
                        doc.close()
                        self._finish_ui()
                        return
                    if not doc.authenticate(pw):
                        doc.close()
                        self._show_error(f"密码错误，无法打开:\n{pdf_path}")
                        self._finish_ui()
                        return
                n = len(doc)
                pdf_pages_list.append((pdf_path, n))
                total_pages += n
                doc.close()
            except Exception as e:
                self._show_error(f"打开 PDF 失败:\n{pdf_path}\n{str(e)}")
                self._finish_ui()
                return

        self.root.after(0, lambda: self.progress.configure(maximum=total_pages))
        self.root.after(0, lambda: self.status_label.configure(
            text=f"共 {total_pages} 页，开始转换...", fg=Theme.TEXT_BODY))

        # 逐文件逐页转换
        for pdf_path, page_count in pdf_pages_list:
            if not self._converting:
                self._finish_ui()
                return

            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            self.root.after(0, lambda n=base_name: self.status_label.configure(
                text=f"正在转换: {n}  ({page_count} 页)", fg=Theme.TEXT_BODY))

            try:
                doc = fitz.open(pdf_path)
                if doc.needs_pass:
                    pw = self._ask_password(os.path.basename(pdf_path))
                    if pw is None:
                        doc.close()
                        self._finish_ui()
                        return
                    if not doc.authenticate(pw):
                        doc.close()
                        self._show_error(f"密码错误，无法打开:\n{pdf_path}")
                        self._finish_ui()
                        return

                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)

                for i in range(page_count):
                    if not self._converting:
                        doc.close()
                        self._finish_ui()
                        return

                    page = doc[i]
                    pix = page.get_pixmap(matrix=mat)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    if page_count == 1:
                        out_name = f"{base_name}.{fmt}"
                    else:
                        out_name = f"{base_name}_p{i+1:03d}.{fmt}"

                    out_path = os.path.join(out_dir, out_name)

                    save_kwargs = {}
                    if fmt == "jpg" or fmt == "jpeg":
                        save_kwargs["quality"] = quality
                        img = img.convert("RGB")
                    elif fmt == "webp":
                        save_kwargs["quality"] = quality
                    elif fmt == "png":
                        save_kwargs["compress_level"] = 6

                    img.save(out_path, **save_kwargs)
                    done_pages += 1

                    self.root.after(0, lambda v=done_pages: self.progress.configure(value=v))
                    self.root.after(0, lambda v=done_pages, t=total_pages:
                                    self.status_label.configure(
                                        text=f"进度: {v}/{t}  页", fg=Theme.TEXT_BODY))

                doc.close()
            except Exception as e:
                self._show_error(f"转换失败:\n{pdf_path}\n{str(e)}")
                self._finish_ui()
                return

        # 完成
        self.root.after(0, lambda: self.progress.configure(value=total_pages))
        self.root.after(0, lambda: self.status_label.configure(
            text=f"完成！共转换 {total_pages} 页 → {out_dir}", fg=Theme.SUCCESS))
        self._finish_ui()

    def _ask_password(self, filename):
        """在主线程弹出密码输入框，返回密码字符串或 None（跳过）"""
        done_event = threading.Event()
        result = [None]  # None = 取消, 字符串 = 密码（可为空串）

        def _dialog():
            dlg = tk.Toplevel(self.root)
            dlg.title("加密 PDF")
            dlg.resizable(False, False)
            dlg.configure(bg=Theme.BG_CARD)
            dlg.transient(self.root)
            dlg.grab_set()

            tk.Label(dlg, text=f"此 PDF 已加密: {filename}",
                     font=("Microsoft YaHei", 10, "bold"),
                     bg=Theme.BG_CARD, fg=Theme.TEXT_TITLE).pack(pady=(18, 8))

            pw_frame = tk.Frame(dlg, bg=Theme.BG_CARD)
            pw_frame.pack()

            tk.Label(pw_frame, text="请输入密码:", font=("Microsoft YaHei", 10),
                     bg=Theme.BG_CARD, fg=Theme.TEXT_BODY).pack(side=tk.LEFT, padx=(0, 6))

            pw_var = tk.StringVar()
            pw_entry = tk.Entry(pw_frame, textvariable=pw_var, show="*",
                                font=("Microsoft YaHei", 10), width=22,
                                relief=tk.SOLID, borderwidth=1)
            pw_entry.pack(side=tk.LEFT)
            pw_entry.focus_set()

            def _ok():
                result[0] = pw_var.get()
                dlg.destroy()

            def _cancel():
                result[0] = None
                dlg.destroy()

            def _on_close():
                result[0] = None
                dlg.destroy()

            dlg.protocol("WM_DELETE_WINDOW", _on_close)

            btn_frame = tk.Frame(dlg, bg=Theme.BG_CARD)
            btn_frame.pack(pady=(14, 0))

            tk.Button(btn_frame, text="确定", command=_ok,
                      font=("Microsoft YaHei", 9),
                      bg=Theme.ACCENT, fg=Theme.TEXT_WHITE,
                      relief=tk.FLAT, cursor="hand2", bd=0, padx=20, pady=4,
                      activebackground=Theme.ACCENT_DEEP).pack(side=tk.LEFT, padx=(0, 10))
            tk.Button(btn_frame, text="跳过此文件", command=_cancel,
                      font=("Microsoft YaHei", 9),
                      bg="#9e9e9e", fg=Theme.TEXT_WHITE,
                      relief=tk.FLAT, cursor="hand2", bd=0, padx=14, pady=4).pack(side=tk.LEFT)

            pw_entry.bind("<Return>", lambda e: _ok())

            # 居中
            dlg.update_idletasks()
            w, h = 380, 160
            px = self.root.winfo_x() + (self.root.winfo_width() - w) // 2
            py = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
            dlg.geometry(f"{w}x{h}+{px}+{py}")

            def _on_destroy():
                done_event.set()

            dlg.bind("<Destroy>", lambda e: _on_destroy())

        self.root.after(0, _dialog)
        done_event.wait()
        return result[0]

    def _show_error(self, msg):
        self.root.after(0, lambda: messagebox.showerror("错误", msg))

    def _finish_ui(self):
        self._converting = False
        self.root.after(0, lambda: self.convert_btn.configure(state=tk.NORMAL))
        self.root.after(0, lambda: self.stop_btn.configure(state=tk.DISABLED))


# ---------------- 入口 ----------------
def main():
    if MISSING_DEPS:
        root = tk.Tk()
        root.withdraw()
        msg = "缺少以下依赖库，请先安装:\n\n" + "\n".join(f"  • {d}" for d in MISSING_DEPS)
        messagebox.showerror("缺少依赖", msg)
        return
    root = tk.Tk()
    app = PDFToImageApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
