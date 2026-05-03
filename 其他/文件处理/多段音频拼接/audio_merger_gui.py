import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import subprocess
import tempfile
from pathlib import Path


class AudioMergerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("音频拼接工具")
        self.root.geometry("600x400")
        self.root.resizable(True, True)

        # 变量
        self.input_folder = tk.StringVar()
        self.output_file = tk.StringVar()
        self.output_format = tk.StringVar(value="mp3")
        self.sort_order = tk.StringVar(value="name")

        self.create_widgets()

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 输入文件夹
        input_frame = ttk.LabelFrame(main_frame, text="输入文件夹", padding="5")
        input_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Entry(input_frame, textvariable=self.input_folder, width=50).grid(
            row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5)
        )
        ttk.Button(input_frame, text="浏览...", command=self.browse_input_folder).grid(
            row=0, column=1
        )

        # 排序方式
        sort_frame = ttk.LabelFrame(main_frame, text="文件排序方式", padding="5")
        sort_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Radiobutton(sort_frame, text="按文件名", variable=self.sort_order, value="name").grid(
            row=0, column=0, padx=10
        )
        ttk.Radiobutton(sort_frame, text="按修改时间", variable=self.sort_order, value="time").grid(
            row=0, column=1, padx=10
        )
        ttk.Radiobutton(sort_frame, text="不排序 (原始顺序)", variable=self.sort_order, value="none").grid(
            row=0, column=2, padx=10
        )

        # 输出设置
        output_frame = ttk.LabelFrame(main_frame, text="输出设置", padding="5")
        output_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(output_frame, text="输出格式:").grid(row=0, column=0, padx=5)
        format_combo = ttk.Combobox(output_frame, textvariable=self.output_format, width=10)
        format_combo["values"] = ("mp3", "wav", "flac", "aac", "m4a", "ogg")
        format_combo.grid(row=0, column=1, padx=5)

        ttk.Label(output_frame, text="输出文件:").grid(row=0, column=2, padx=5)
        ttk.Entry(output_frame, textvariable=self.output_file, width=30).grid(
            row=0, column=3, padx=(0, 5)
        )
        ttk.Button(output_frame, text="选择...", command=self.browse_output_file).grid(
            row=0, column=4
        )

        # 文件列表
        list_frame = ttk.LabelFrame(main_frame, text="待处理文件列表", padding="5")
        list_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(3, weight=1)

        # 创建 Treeview 显示文件
        columns = ("序号", "文件名", "时长", "大小")
        self.file_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        for col in columns:
            self.file_tree.heading(col, text=col)
            self.file_tree.column(col, width=(80 if col != "文件名" else 300))

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=scrollbar.set)

        self.file_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="加载文件", command=self.load_files).grid(
            row=0, column=0, padx=5
        )
        ttk.Button(button_frame, text="开始拼接", command=self.merge_audio).grid(
            row=0, column=1, padx=5
        )
        ttk.Button(button_frame, text="清空列表", command=self.clear_list).grid(
            row=0, column=2, padx=5
        )

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(5, 0))

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

    def browse_input_folder(self):
        folder = filedialog.askdirectory(title="选择包含音频文件的文件夹")
        if folder:
            self.input_folder.set(folder)
            self.load_files()

    def browse_output_file(self):
        formats = {
            "mp3": ("MP3 文件", "*.mp3"),
            "wav": ("WAV 文件", "*.wav"),
            "flac": ("FLAC 文件", "*.flac"),
            "aac": ("AAC 文件", "*.aac"),
            "m4a": ("M4A 文件", "*.m4a"),
            "ogg": ("OGG 文件", "*.ogg"),
        }
        filetypes = [formats[self.output_format.get()]]
        filetypes.append(("所有文件", "*.*"))

        filename = filedialog.asksaveasfilename(
            title="选择输出文件位置",
            filetypes=filetypes,
            defaultextension=f".{self.output_format.get()}"
        )
        if filename:
            self.output_file.set(filename)

    def get_audio_files(self, folder):
        """获取文件夹中的所有音频文件"""
        audio_extensions = {
            ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg",
            ".wma", ".ape", ".alac", ".opus", ".webm"
        }

        files = []
        for f in os.listdir(folder):
            ext = Path(f).suffix.lower()
            if ext in audio_extensions:
                files.append(os.path.join(folder, f))

        # 排序
        if self.sort_order.get() == "name":
            files.sort(key=lambda x: os.path.basename(x))
        elif self.sort_order.get() == "time":
            files.sort(key=lambda x: os.path.getmtime(x))

        return files

    def get_file_duration(self, filepath):
        """使用 ffprobe 获取音频时长"""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=10, encoding='utf-8', errors='replace')
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return f"{int(duration // 60):02d}:{int(duration % 60):02d}"
        except Exception:
            pass
        return "未知"

    def get_file_size(self, filepath):
        """获取文件大小"""
        size = os.path.getsize(filepath)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"

    def load_files(self):
        """加载文件到列表"""
        folder = self.input_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("警告", "请先选择有效的输入文件夹")
            return

        self.clear_list()
        files = self.get_audio_files(folder)

        if not files:
            messagebox.showinfo("提示", "文件夹中没有找到音频文件")
            return

        for i, filepath in enumerate(files, 1):
            filename = os.path.basename(filepath)
            duration = self.get_file_duration(filepath)
            size = self.get_file_size(filepath)
            self.file_tree.insert("", "end", values=(i, filename, duration, size))

        self.status_var.set(f"已加载 {len(files)} 个音频文件")

        # 自动设置输出文件名
        if not self.output_file.get():
            folder_name = os.path.basename(folder)
            self.output_file.set(os.path.join(folder, f"{folder_name}_merged.{self.output_format.get()}"))

    def clear_list(self):
        """清空文件列表"""
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

    def check_ffmpeg(self):
        """检查 FFmpeg 是否可用"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, encoding='utf-8', errors='replace')
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def merge_audio(self):
        """合并音频文件"""
        folder = self.input_folder.get()
        output = self.output_file.get()

        if not folder or not os.path.isdir(folder):
            messagebox.showerror("错误", "请选择有效的输入文件夹")
            return

        if not output:
            messagebox.showerror("错误", "请选择输出文件位置")
            return

        files = self.get_audio_files(folder)
        if not files:
            messagebox.showerror("错误", "没有找到可处理的音频文件")
            return

        if not self.check_ffmpeg():
            messagebox.showerror("错误", "未找到 FFmpeg，请先安装 FFmpeg 并添加到系统 PATH")
            return

        # 创建临时文件列表
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            list_file = f.name
            for filepath in files:
                # Windows 路径需要转义单引号
                escaped_path = filepath.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")

        try:
            self.status_var.set("正在拼接音频...")
            self.progress.start()
            self.root.update()

            # 构建 FFmpeg 命令
            cmd = [
                "ffmpeg",
                "-y",  # 覆盖输出
                "-f", "concat",
                "-safe", "0",
                "-i", list_file,
                "-c", "copy" if self.output_format.get() in ["mp3", "wav", "m4a"] else "libfdk_aac",
                output
            ]

            # 对于某些格式需要重新编码
            if self.output_format.get() == "mp3":
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file,
                    "-c:a", "libmp3lame",
                    "-q:a", "2",
                    output
                ]
            elif self.output_format.get() == "flac":
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file,
                    "-c:a", "flac",
                    output
                ]

            result = subprocess.run(cmd, capture_output=True, timeout=600, encoding='utf-8', errors='replace')

            if result.returncode != 0:
                messagebox.showerror("错误", f"FFmpeg 处理失败:\n{result.stderr[:500]}")
                self.status_var.set("处理失败")
            else:
                messagebox.showinfo("成功", f"音频拼接完成!\n输出文件：{output}")
                self.status_var.set(f"处理完成，共处理 {len(files)} 个文件")

        except subprocess.TimeoutExpired:
            messagebox.showerror("错误", "处理超时，文件可能过大")
            self.status_var.set("处理超时")
        except Exception as e:
            messagebox.showerror("错误", f"处理失败：{str(e)}")
            self.status_var.set("处理失败")
        finally:
            self.progress.stop()
            # 清理临时文件
            if os.path.exists(list_file):
                os.unlink(list_file)


def main():
    root = tk.Tk()
    app = AudioMergerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
