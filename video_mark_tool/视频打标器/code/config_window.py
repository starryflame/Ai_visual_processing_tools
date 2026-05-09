import tkinter as tk
from tkinter import messagebox


class ConfigWindow:
    """配置编辑窗口，展示并允许编辑 config.ini 中的配置项"""

    # 显示分组与字段标签映射
    SECTION_LABELS = {
        'MODEL': '模型生成参数',
        'VIDEO': '视频设置',
        'UI': '界面设置',
        'PROCESSING': '处理参数',
        'LLM': 'API 服务配置',
        'PROMPTS': '提示词',
        'FILTER': '过滤关键词',
        'FILTER_WORDS': '过滤词（重新生成触发）',
    }

    FIELD_LABELS = {
        'max_new_tokens': '最大生成 token 数',
        'retry_max_new_tokens': '重试时最大 token 数',
        'temperature': '温度参数',
        'top_p': 'top-p 参数',
        'default_export_fps': '默认导出帧率',
        'export_path': '导出路径',
        'window_width': '窗口宽度',
        'window_height': '窗口高度',
        'target_frame_height': '目标帧高度',
        'max_size': '最大尺寸',
        'max_sample_frames': '最大采样帧数',
        'target_frame_rate': '目标帧率',
        'segment_duration': '自动分段时长(秒)',
        'max_filename_length': '导出文件名最大长度',
        'api_base_url': 'API 地址',
        'api_key': 'API Key',
        'model_name1': '模型名称1',
        'model_name': '模型名称',
        'max_tokens': '最大生成 token 数',
        'video_prompt': '视频提示词',
        'keywords': '过滤关键词',
        'words': '重新生成触发词',
    }

    # 多行文本字段
    MULTI_LINE_FIELDS = {'video_prompt', 'keywords', 'words'}

    def __init__(self, parent, config, config_path, on_save=None):
        self.parent = parent
        self.config = config
        self.config_path = config_path
        self.on_save = on_save
        self.entries = {}  # { (section, key): tk.Entry }

        self.win = tk.Toplevel(parent)
        self.win.title("配置编辑")
        self.win.geometry("600x600")
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
        section_order = ['MODEL', 'VIDEO', 'UI', 'PROCESSING', 'LLM', 'PROMPTS', 'FILTER', 'FILTER_WORDS']

        row = 0
        for section in section_order:
            if section not in self.config:
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
        for (section, key), widget in self.entries.items():
            value = self._get_value(widget)
            self.config.set(section, key, value)

        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                self.config.write(f)
            messagebox.showinfo("成功", "配置已保存")
            if self.on_save:
                self.on_save()
            self._on_close()
        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{e}")

    def _restore(self):
        """重新从文件读取配置并刷新界面"""
        self.config.read(self.config_path, encoding='utf-8')
        for (section, key), widget in self.entries.items():
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
