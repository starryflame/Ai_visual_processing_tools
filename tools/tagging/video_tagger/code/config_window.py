import os
import tkinter as tk
from tkinter import messagebox


class ConfigWindow:
    """配置编辑窗口，展示并允许编辑 config.ini 中的配置项以及 video_prompt.txt"""

    # 显示分组与字段标签映射
    SECTION_LABELS = {
        'MODEL': '模型生成参数',
        'VIDEO': '视频设置',
        'UI': '界面设置',
        'PROCESSING': '视频处理参数',
        'PROMPTS': '提示词',
        'FILTER_WORDS': '过滤词（重新生成触发）',
    }

    FIELD_LABELS = {
        'model_name': '模型名称',
        'max_new_tokens': '最大生成 token 数',
        'temperature': '温度参数',
        'top_p': 'top-p 参数',
        'default_export_fps': '默认导出帧率',
        'export_path': '导出路径',
        'window_width': '窗口宽度',
        'window_height': '窗口高度',
        'target_max_edge': '目标最长边',
        'max_sample_frames': '最大采样帧数',
        'target_frame_rate': '目标帧率',
        'segment_duration': '自动分段时长(秒)',
        'image_max_size': 'AI 图像最大边长',
        'api_base_url': 'API 地址',
        'api_key': 'API Key',
        'video_prompt': '视频提示词',
        'words': '重新生成触发词',
    }

    # 多行文本字段
    MULTI_LINE_FIELDS = {'words'}

    # 隐藏字段（已在外部文件中管理）
    HIDDEN_FIELDS = {'video_prompt'}

    # 从 config.ini 路径推导 video_prompt.txt 路径
    def _get_prompt_path(self):
        return os.path.join(os.path.dirname(self.config_path), "video_prompt.txt")

    def __init__(self, parent, config, config_path, on_save=None):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.on_save = on_save
        self.entries = {}  # { (section, key): tk.Entry }

        self.win = tk.Toplevel(parent)
        self.win.title("配置编辑")
        self.win.geometry("600x700")
        self.win.transient(parent)
        self.win.grab_set()

        # 主滚动区域
        canvas = tk.Canvas(self.win)
        scrollbar = tk.Scrollbar(self.win, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="top", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 按顺序展示各 section
        section_order = ['MODEL', 'VIDEO', 'UI', 'PROCESSING', 'PROMPTS', '_PROMPT_FILE', 'FILTER_WORDS']

        # 从 config.ini 路径推导 video_prompt.txt 路径
        prompt_path = self._get_prompt_path()
        prompt_content = ""
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_content = f.read()
        except FileNotFoundError:
            prompt_content = ""

        row = 0
        for section in section_order:
            if section == '_PROMPT_FILE':
                # AI 提示词文件编辑器
                tk.Label(
                    self.scrollable_frame, text="AI 提示词（video_prompt.txt）",
                    font=("Microsoft YaHei", 10, "bold"),
                    fg="#2c3e50", anchor="w"
                ).grid(row=row, column=0, sticky="ew", padx=15, pady=(12, 6))
                row += 1

                sep = tk.Frame(self.scrollable_frame, height=1, bg="#dcdde1")
                sep.grid(row=row, column=0, sticky="ew", padx=15)
                row += 1

                txt = tk.Text(self.scrollable_frame, height=15, font=("Consolas", 9))
                txt.insert("1.0", prompt_content)
                txt.grid(row=row, column=0, sticky="ew", padx=15, pady=(0, 2))
                self.entries[('_PROMPT_FILE', 'content')] = txt
                row += 1
                continue

            if section not in self.config:
                continue

            # 检查 section 下是否有可见字段
            visible_keys = [k for k in self.config[section] if k not in self.HIDDEN_FIELDS]
            if not visible_keys:
                continue

            # section 标题
            label_text = self.SECTION_LABELS.get(section, section)
            section_label = tk.Label(
                self.scrollable_frame, text=label_text,
                font=("Microsoft YaHei", 10, "bold"),
                fg="#2c3e50", anchor="w"
            )
            section_label.grid(row=row, column=0, sticky="ew", padx=15, pady=(12, 6))
            row += 1

            # 分隔线
            sep = tk.Frame(self.scrollable_frame, height=1, bg="#dcdde1")
            sep.grid(row=row, column=0, sticky="ew", padx=15)
            row += 1

            for key in self.config[section]:
                if key in self.HIDDEN_FIELDS:
                    continue
                display_key = self.FIELD_LABELS.get(key, key)
                value = self.config[section][key]

                tk.Label(
                    self.scrollable_frame, text=display_key,
                    font=("Microsoft YaHei", 9), anchor="w"
                ).grid(row=row, column=0, sticky="w", padx=15, pady=(6, 2))
                row += 1

                if key in self.MULTI_LINE_FIELDS:
                    txt = tk.Text(self.scrollable_frame, height=3, font=("Consolas", 9))
                    txt.insert("1.0", value)
                    txt.grid(row=row, column=0, sticky="ew", padx=15, pady=(0, 2))
                    self.entries[(section, key)] = txt
                else:
                    entry = tk.Entry(self.scrollable_frame, font=("Consolas", 9))
                    entry.insert(0, value)
                    entry.grid(row=row, column=0, sticky="ew", padx=15, pady=(0, 2))
                    self.entries[(section, key)] = entry
                row += 1

        self.scrollable_frame.grid_columnconfigure(0, weight=1)

        # 按钮区
        btn_frame = tk.Frame(self.win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(btn_frame, text="保存", command=self._save, font=("Microsoft YaHei", 10), width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="取消", command=self._on_close, font=("Microsoft YaHei", 10), width=10).pack(side=tk.RIGHT, padx=5)
        tk.Button(btn_frame, text="恢复默认", command=self._restore, font=("Microsoft YaHei", 10), width=10).pack(side=tk.LEFT, padx=5)

        # 滚动绑定（绑定到 scrollable_frame 及其所有子控件）
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                pass

        def _bind_all(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                _bind_all(child)

        _bind_all(self.scrollable_frame)

        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

    def _get_value(self, widget):
        """从控件中获取当前值"""
        if isinstance(widget, tk.Text):
            return widget.get("1.0", "end-1c").strip()
        return widget.get().strip()

    def _save(self):
        # 保存 prompt 文件
        if ('_PROMPT_FILE', 'content') in self.entries:
            prompt_text = self.entries[('_PROMPT_FILE', 'content')].get("1.0", "end-1c").strip()
            prompt_path = self._get_prompt_path()
            try:
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(prompt_text + "\n")
            except Exception as e:
                messagebox.showerror("错误", f"提示词保存失败：{e}")
                return

        # 保存 config.ini
        updates = {}
        for (section, key), widget in self.entries.items():
            if section == '_PROMPT_FILE':
                continue
            updates.setdefault(section, {})[key] = self._get_value(widget)

        try:
            lines = open(self.config_path, 'r', encoding='utf-8').readlines()
            current_section = None
            for i, line in enumerate(lines):
                stripped = line.strip()
                # 检测 section 头
                if stripped.startswith('[') and stripped.endswith(']'):
                    current_section = stripped[1:-1]
                # 替换 key = value 行
                elif '=' in stripped and current_section and current_section in updates:
                    key = stripped.split('=', 1)[0].strip()
                    if key in updates[current_section]:
                        lines[i] = f'{key} = {updates[current_section][key]}\n'
                        del updates[current_section][key]

            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)

            messagebox.showinfo("成功", "配置已保存")
            if self.on_save:
                self.on_save()
            self._on_close()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def _restore(self):
        """重新从文件读取配置并刷新界面"""
        self.config.read(self.config_path, encoding='utf-8')

        # 重新加载 prompt 文件
        if ('_PROMPT_FILE', 'content') in self.entries:
            prompt_path = self._get_prompt_path()
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except FileNotFoundError:
                content = ""
            widget = self.entries[('_PROMPT_FILE', 'content')]
            widget.delete("1.0", "end")
            widget.insert("1.0", content)

        for (section, key), widget in self.entries.items():
            if section == '_PROMPT_FILE':
                continue
            value = self.config.get(section, key, fallback='')
            if isinstance(widget, tk.Text):
                widget.delete("1.0", "end")
                widget.insert("1.0", value)
            else:
                widget.delete(0, tk.END)
                widget.insert(0, value)
        messagebox.showinfo("提示", "已恢复为文件中的配置")

    def _on_close(self):
        if not self.win.winfo_exists():
            return
        self.win.destroy()
