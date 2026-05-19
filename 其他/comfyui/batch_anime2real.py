#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 批量动漫转写实处理脚本 - GUI 版本
使用方法：直接运行，通过图形界面选择文件夹
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import json
import requests
import uuid
import time
import os
import random
from pathlib import Path
import threading


class ComfyUIBatchProcessor:
    """ComfyUI 批量处理器"""
    
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.workflow_path = r"J:\Ai_visual_processing_tools\其他\comfyui\工作流\动漫转写实真人2511（AnythingtoRealCharacters）正式版-高还原2.json"
        
    def load_workflow(self):
        """加载工作流配置"""
        with open(self.workflow_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def queue_prompt(self, prompt):
        """提交任务到 ComfyUI"""
        url = f"http://{self.server_address}/prompt"
        data = {"prompt": prompt}
        response = requests.post(url, json=data)
        return response.json()
    
    def get_history(self, prompt_id):
        """获取任务历史"""
        url = f"http://{self.server_address}/history/{prompt_id}"
        response = requests.get(url)
        return response.json()
    
    def get_image(self, filename, subfolder, folder_type):
        """获取生成的图片"""
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url = f"http://{self.server_address}/view"
        response = requests.get(url, params=params)
        return response.content
    
    def process_image(self, workflow, input_image_path, output_folder, original_folder, output_image_folder, prompt, lora_name, resize_longest_edge=1440):
        """处理单张图片"""
        # 修改 LoadImage 节点的输入图片
        workflow["78"]["inputs"]["image"] = input_image_path

        # 修改提示词（节点 110）
        if "110" in workflow:
            workflow["110"]["inputs"]["prompt"] = prompt

        # 修改 LoRA 路径（节点 337）
        if "337" in workflow:
            workflow["337"]["inputs"]["lora_name"] = lora_name

        # 修改缩放最长边长度（节点 301）
        if "301" in workflow:
            workflow["301"]["inputs"]["scale_to_length"] = resize_longest_edge

        # 随机化采样种子，确保每次生成结果不同
        if "3" in workflow and "seed" in workflow["3"]["inputs"]:
            max_seed = 2**64 - 1
            workflow["3"]["inputs"]["seed"] = random.randint(0, max_seed)

        # 提交任务
        result = self.queue_prompt(workflow)
        if "prompt_id" not in result:
            return False, "任务提交失败"

        prompt_id = result["prompt_id"]

        # 等待任务完成
        max_wait = 300  # 最大等待 5 分钟
        start_time = time.time()
        while time.time() - start_time < max_wait:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                # 任务完成，保存图片
                outputs = history[prompt_id]["outputs"]
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        for img in node_output["images"]:
                            img_data = self.get_image(img["filename"], img.get("subfolder", ""), img.get("type", "output"))
                            # 生成输出文件名 - 保持与原图相同的扩展名
                            original_ext = Path(input_image_path).suffix.lower()
                            output_name = f"{Path(input_image_path).stem}{original_ext}"
                            output_path = os.path.join(output_image_folder, output_name)
                            with open(output_path, 'wb') as f:
                                f.write(img_data)
                            # 复制原图到原图文件夹 - 保持相同文件名和格式
                            original_path = os.path.join(original_folder, Path(input_image_path).name)
                            with open(input_image_path, 'rb') as src:
                                with open(original_path, 'wb') as dst:
                                    dst.write(src.read())
                            return True, output_path
            time.sleep(1)

        return False, "任务超时"


class BatchProcessorGUI:
    """批量处理 GUI 界面"""

    PRESETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompt_presets.json")

    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI 批量动漫转写实处理")
        self.root.geometry("1200x800")

        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.prompt_text = tk.StringVar(value="动漫转真人，无水印")
        self.lora_path = tk.StringVar(value=r"qwen_edit\自创\动漫转真人_我的人物_000002000.safetensors")
        # 用于存储完整路径的映射
        self.lora_full_paths = {}
        self.start_index = tk.IntVar(value=0)
        self.resize_longest_edge = tk.IntVar(value=1440)
        self.process_mode = tk.StringVar(value="全自动模式")  # 全自动模式/半自动模式
        self.processor = ComfyUIBatchProcessor()

        # 控制变量
        self.is_running = False
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_flag = False
        self.image_files = []
        self.current_thread = None
        self.current_index = 0  # 当前处理索引
        self.total_count = 0    # 总数

        # 半自动模式专用
        self.semi_result = None  # None=等待中，"next"=下一张，"retry"=重新生成，"stop"=停止
        self.semi_done_event = threading.Event()
        self.semi_dialog_ref = None  # 用于持有对话框引用，更新下一张预览
        self.prompt_presets = self._load_presets()

        # 日志区折叠状态
        self.log_expanded = True

        # 图片预览
        self.input_photo = None
        self.output_photo = None
        self.semi_next_photo = None  # 半自动对话框中下一张预览
        self.current_input_img = None
        self.current_output_img = False

        # 控制面板隐藏状态
        self.control_panel_hidden = False

        self.create_widgets()

        # 绑定 ESC 键退出全屏
        self.root.bind('<Escape>', lambda _: self.toggle_fullscreen())
        # 绑定 F11 切换全屏
        self.root.bind('<F11>', lambda _: self.toggle_fullscreen())
        # 绑定 Tab 键切换控制面板
        self.root.bind('<Tab>', lambda _: self.toggle_control_panel())
    
    def create_widgets(self):
        """创建界面组件"""
        # 主容器 - 上下分栏
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 上部 - 控制面板
        self.control_frame = tk.Frame(main_container)
        self.control_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)

        # 下部 - 实时图片预览 - 占据剩余所有空间
        self.bottom_frame = tk.Frame(main_container, bg='#1a1a1a', relief=tk.RAISED, bd=2)
        self.bottom_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.create_control_panel(self.control_frame)
        self.create_preview_panel(self.bottom_frame)

        # 全屏提示标签
        self.fullscreen_hint = tk.Label(
            self.root,
            text="F11 全屏 | ESC 退出 | Tab 隐藏控制面板",
            font=("Microsoft YaHei UI", 9),
            fg="#888",
            bg="#f0f0f0"
        )
        self.fullscreen_hint.pack(anchor=tk.W, padx=10, pady=(0, 5))

    def create_control_panel(self, parent):
        """创建左侧控制面板"""
        # 输入文件夹选择
        input_frame = tk.Frame(parent, pady=5)
        input_frame.pack(fill=tk.X)
        tk.Label(input_frame, text="输入文件夹:", width=12).pack(side=tk.LEFT)
        tk.Entry(input_frame, textvariable=self.input_folder).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(input_frame, text="浏览", command=self.select_input_folder, width=8).pack(side=tk.LEFT)

        # 输出文件夹选择
        output_frame = tk.Frame(parent, pady=5)
        output_frame.pack(fill=tk.X)
        tk.Label(output_frame, text="输出文件夹:", width=12).pack(side=tk.LEFT)
        tk.Entry(output_frame, textvariable=self.output_folder).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(output_frame, text="浏览", command=self.select_output_folder, width=8).pack(side=tk.LEFT)

        # 提示词输入
        prompt_frame = tk.Frame(parent, pady=5)
        prompt_frame.pack(fill=tk.X)
        tk.Label(prompt_frame, text="提示词:", width=12).pack(side=tk.LEFT)
        tk.Entry(prompt_frame, textvariable=self.prompt_text).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 模式选择 - 下拉框
        mode_frame = tk.Frame(parent, pady=5)
        mode_frame.pack(fill=tk.X)
        tk.Label(mode_frame, text="处理模式:", width=12).pack(side=tk.LEFT)
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.process_mode, state="readonly", width=20)
        mode_combo['values'] = ["全自动模式", "半自动模式"]
        mode_combo.pack(side=tk.LEFT, padx=5)
        # 设置默认值
        mode_combo.current(0)

        # LoRA 路径选择 - 下拉框
        lora_frame = tk.Frame(parent, pady=5)
        lora_frame.pack(fill=tk.X)
        tk.Label(lora_frame, text="LoRA 路径:", width=12).pack(side=tk.LEFT)
        self.lora_combo = ttk.Combobox(lora_frame, textvariable=self.lora_path, state="readonly")
        self.lora_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        tk.Button(lora_frame, text="刷新", command=self.load_lora_models, width=6).pack(side=tk.LEFT, padx=2)
        # 加载模型列表
        self.load_lora_models()

        # 缩放最长边输入
        resize_frame = tk.Frame(parent, pady=5)
        resize_frame.pack(fill=tk.X)
        tk.Label(resize_frame, text="缩放最长边:", width=12).pack(side=tk.LEFT)
        self.resize_spinbox = tk.Spinbox(resize_frame, textvariable=self.resize_longest_edge, from_=256, to=8192, width=10)
        self.resize_spinbox.pack(side=tk.LEFT, padx=5)
        tk.Label(resize_frame, text="(像素，默认1440)", fg="#666").pack(side=tk.LEFT)

        # 起始索引输入
        index_frame = tk.Frame(parent, pady=5)
        index_frame.pack(fill=tk.X)
        tk.Label(index_frame, text="从第几个开始:", width=12).pack(side=tk.LEFT)
        self.start_index_spinbox = tk.Spinbox(index_frame, textvariable=self.start_index, from_=0, to=9999, width=10)
        self.start_index_spinbox.pack(side=tk.LEFT, padx=5)
        tk.Label(index_frame, text="(0 表示从第一个开始)", fg="#666").pack(side=tk.LEFT)

        # 进度条
        progress_frame = tk.Frame(parent, pady=10)
        progress_frame.pack(fill=tk.X)
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)
        self.progress_label = tk.Label(progress_frame, text="准备就绪", font=("Consolas", 10))
        self.progress_label.pack()

        # 控制按钮行
        button_frame = tk.Frame(parent, pady=10)
        button_frame.pack()

        self.start_button = tk.Button(button_frame, text="开始处理", command=self.start_processing, width=15, bg="#4CAF50", fg="white")
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = tk.Button(button_frame, text="暂停", command=self.pause_processing, width=10, state=tk.DISABLED, bg="#FF9800", fg="white")
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.resume_button = tk.Button(button_frame, text="继续", command=self.resume_processing, width=10, state=tk.DISABLED, bg="#2196F3", fg="white")
        self.resume_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(button_frame, text="停止", command=self.stop_processing, width=10, state=tk.DISABLED, bg="#f44336", fg="white")
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # 日志区域 - 添加折叠按钮
        log_frame = tk.Frame(parent, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # 日志标题栏
        log_header_frame = tk.Frame(log_frame)
        log_header_frame.pack(fill=tk.X, anchor=tk.W)

        tk.Label(log_header_frame, text="处理日志:").pack(side=tk.LEFT)

        self.log_toggle_button = tk.Button(
            log_header_frame,
            text="▲ 收起",
            command=self.toggle_log,
            width=8,
            font=("Microsoft YaHei UI", 9)
        )
        self.log_toggle_button.pack(side=tk.RIGHT)

        # 日志文本区域 - 放在单独 frame 中以便折叠
        self.log_container = tk.Frame(log_frame)
        self.log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(self.log_container, height=8, width=60)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_preview_panel(self, parent):
        """创建底部图片预览面板"""
        # 标题栏
        self.title_label = tk.Label(
            parent,
            text="🖼️ 实时预览 - 输入/输出对比",
            font=("Microsoft YaHei UI", 16, "bold"),
            bg='#1a1a1a',
            fg='white'
        )
        self.title_label.pack(pady=10)

        # 图片容器 - 左右并排
        imgs_container = tk.Frame(parent, bg='#1a1a1a')
        imgs_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # 输入图区域 - 靠右对齐（右边距为 0）
        input_preview_frame = tk.Frame(imgs_container, bg='#2a2a2a', relief=tk.RAISED, bd=0)
        input_preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0), pady=0)

        self.input_label = tk.Label(
            input_preview_frame,
            text="输入图 (原图)",
            font=("Microsoft YaHei UI", 14, "bold"),
            bg='#2a2a2a',
            fg='#2196F3'
        )
        self.input_label.pack(pady=5)

        # 使用 Canvas 显示图片，支持靠右对齐
        self.input_canvas = tk.Canvas(input_preview_frame, bg='#1a1a1a', highlightthickness=0)
        self.input_canvas.pack(fill=tk.BOTH, expand=True)
        self.input_image_id = self.input_canvas.create_image(0, 0, anchor=tk.NE, image=None)

        # 输出图区域 - 靠左对齐（左边距为 0）
        output_preview_frame = tk.Frame(imgs_container, bg='#2a2a2a', relief=tk.RAISED, bd=0)
        output_preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 0), pady=0)

        self.output_label = tk.Label(
            output_preview_frame,
            text="输出图 (生成结果)",
            font=("Microsoft YaHei UI", 14, "bold"),
            bg='#2a2a2a',
            fg='#4CAF50'
        )
        self.output_label.pack(pady=5)

        # 使用 Canvas 显示图片，支持靠左对齐
        self.output_canvas = tk.Canvas(output_preview_frame, bg='#1a1a1a', highlightthickness=0)
        self.output_canvas.pack(fill=tk.BOTH, expand=True)
        self.output_image_id = self.output_canvas.create_image(0, 0, anchor=tk.NW, image=None)

    def toggle_fullscreen(self):
        """切换全屏模式"""
        current = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current)

        if not current:
            # 进入全屏
            self.fullscreen_hint.pack_forget()
        else:
            # 退出全屏
            self.fullscreen_hint.pack(anchor=tk.W, padx=10, pady=(0, 5))

    def toggle_control_panel(self):
        """切换控制面板显示/隐藏"""
        if self.control_panel_hidden:
            # 使用 before 参数确保放在 bottom_frame 之前
            self.control_frame.pack(fill=tk.X, expand=False, padx=10, pady=10, before=self.bottom_frame)
            self.title_label.pack(pady=10)
            self.input_label.pack(pady=5)
            self.output_label.pack(pady=5)
            self.control_panel_hidden = False
        else:
            self.control_frame.pack_forget()
            self.title_label.pack_forget()
            self.input_label.pack_forget()
            self.output_label.pack_forget()
            self.control_panel_hidden = True

    def toggle_log(self):
        """切换日志区显示/隐藏"""
        if self.log_expanded:
            # 收起日志区
            self.log_container.pack_forget()
            self.log_toggle_button.config(text="▼ 展开")
            self.log_expanded = False
        else:
            # 展开日志区
            self.log_container.pack(fill=tk.BOTH, expand=True)
            self.log_toggle_button.config(text="▲ 收起")
            self.log_expanded = True

    def resize_image(self, img, max_width, max_height):
        """缩放图片以填充显示区域（小图放大，大图缩小）"""
        if max_width <= 0 or max_height <= 0:
            return img

        target_width = max_width - 20
        target_height = max_height - 20

        ratio = min(target_width / img.width, target_height / img.height)

        if ratio != 1:
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return img

    def update_input_preview(self, image_path):
        """更新输入图预览"""
        try:
            img = Image.open(image_path)
            canvas_width = self.input_canvas.winfo_width()
            canvas_height = self.input_canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 400
                canvas_height = 300

            img = self.resize_image(img, canvas_width, canvas_height)
            self.input_photo = ImageTk.PhotoImage(img)

            # 更新 Canvas 图片，靠右对齐 (anchor=tk.NE)
            self.input_canvas.itemconfig(self.input_image_id, image=self.input_photo)
            self.input_canvas.coords(self.input_image_id, (canvas_width, 0))
        except Exception as e:
            print(f"显示输入预览错误：{e}")

    def update_output_preview(self, image_path):
        """更新输出图预览"""
        try:
            img = Image.open(image_path)
            canvas_width = self.output_canvas.winfo_width()
            canvas_height = self.output_canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = 400
                canvas_height = 300

            img = self.resize_image(img, canvas_width, canvas_height)
            self.output_photo = ImageTk.PhotoImage(img)

            # 更新 Canvas 图片，靠左对齐 (anchor=tk.NW)
            self.output_canvas.itemconfig(self.output_image_id, image=self.output_photo)
            self.output_canvas.coords(self.output_image_id, (0, 0))
        except Exception as e:
            print(f"显示输出预览错误：{e}")

    def update_both_previews(self, input_path, output_path):
        """同时更新输入图和输出图预览，确保配对正确"""
        try:
            # 读取输入图
            input_img = Image.open(input_path)
            input_canvas_width = self.input_canvas.winfo_width()
            input_canvas_height = self.input_canvas.winfo_height()
            if input_canvas_width <= 1 or input_canvas_height <= 1:
                input_canvas_width = self.root.winfo_width() // 2
                input_canvas_height = self.root.winfo_height() // 2

            input_img = self.resize_image(input_img, input_canvas_width, input_canvas_height)
            self.input_photo = ImageTk.PhotoImage(input_img)
            self.input_canvas.itemconfig(self.input_image_id, image=self.input_photo)
            self.input_canvas.coords(self.input_image_id, (input_canvas_width, 0))  # 靠右对齐

            # 读取输出图
            output_img = Image.open(output_path)
            output_canvas_width = self.output_canvas.winfo_width()
            output_canvas_height = self.output_canvas.winfo_height()
            if output_canvas_width <= 1 or output_canvas_height <= 1:
                output_canvas_width = self.root.winfo_width() // 2
                output_canvas_height = self.root.winfo_height() // 2

            output_img = self.resize_image(output_img, output_canvas_width, output_canvas_height)
            self.output_photo = ImageTk.PhotoImage(output_img)
            self.output_canvas.itemconfig(self.output_image_id, image=self.output_photo)
            self.output_canvas.coords(self.output_image_id, (0, 0))  # 靠左对齐

        except Exception as e:
            print(f"显示预览错误：{e}")
    
    def select_input_folder(self):
        """选择输入文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.input_folder.set(folder)
    
    def select_output_folder(self):
        """选择输出文件夹"""
        folder = filedialog.askdirectory()
        if folder:
            self.output_folder.set(folder)

    def load_lora_models(self):
        """加载 LoRA 模型列表"""
        lora_folder = r"J:\models\loras\qwen_edit\自创"
        base_path = r"J:\models\loras"

        if os.path.exists(lora_folder):
            model_files = []
            # 遍历文件夹获取所有文件
            for root, _, files in os.walk(lora_folder):
                for file in files:
                    if file.lower().endswith('.safetensors') or file.lower().endswith('.pt') or file.lower().endswith('.pth'):
                        # 存储完整路径
                        full_path = os.path.join(root, file)
                        # 生成相对路径（从 qwen_edit\自创 开始）
                        rel_path = os.path.relpath(full_path, base_path)
                        model_files.append(rel_path)
                        # 保存相对路径到完整路径的映射
                        self.lora_full_paths[rel_path] = full_path

            # 设置下拉框选项
            self.lora_combo['values'] = model_files

            # 设置默认选中项
            if model_files:
                default_model = r"qwen_edit\自创\动漫转真人_我的人物_000002000.safetensors"
                if default_model in model_files:
                    self.lora_path.set(default_model)
                else:
                    self.lora_path.set(model_files[0])
        else:
            messagebox.showwarning("警告", f"模型文件夹不存在：{lora_folder}")

    def _load_presets(self):
        """加载提示词预设"""
        if os.path.exists(self.PRESETS_FILE):
            try:
                with open(self.PRESETS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_presets(self):
        """保存提示词预设到文件"""
        try:
            with open(self.PRESETS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.prompt_presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存预设失败: {e}")
    
    def log(self, message):
        """添加日志"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def start_processing(self):
        """开始处理"""
        input_folder = self.input_folder.get()
        output_folder = self.output_folder.get()

        if not input_folder or not output_folder:
            messagebox.showerror("错误", "请选择输入和输出文件夹")
            return

        # 获取所有图片文件
        image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
        self.image_files = [f for f in os.listdir(input_folder)
                           if Path(f).suffix.lower() in image_extensions]

        if not self.image_files:
            messagebox.showwarning("警告", "输入文件夹中没有找到图片文件")
            return

        # 获取起始索引
        start_idx = self.start_index.get()
        if start_idx < 0 or start_idx >= len(self.image_files):
            messagebox.showerror("错误", f"起始索引超出范围 (0-{len(self.image_files)-1})")
            return

        # 重置控制变量
        self.is_running = True
        self.is_paused = False
        self.stop_flag = False
        self.pause_event.set()
        self.current_index = start_idx
        self.total_count = len(self.image_files)

        # 更新按钮状态
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # 禁用起始索引输入框
        self.start_index_spinbox.config(state=tk.DISABLED)

        # 启动线程处理
        self.current_thread = threading.Thread(
            target=self.process_batch,
            args=(input_folder, output_folder, self.image_files, start_idx)
        )
        self.current_thread.start()

    def pause_processing(self):
        """暂停处理"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.pause_event.clear()
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.NORMAL)
            self.log(f"⏸ 已暂停 - {self.current_index + 1}/{self.total_count}")

    def resume_processing(self):
        """继续处理"""
        if self.is_paused:
            self.is_paused = False
            self.pause_event.set()
            self.pause_button.config(state=tk.NORMAL)
            self.resume_button.config(state=tk.DISABLED)
            self.log(f"▶ 已继续 - {self.current_index + 1}/{self.total_count}")

    def stop_processing(self):
        """停止处理"""
        if self.is_running:
            if messagebox.askyesno("确认", "确定要停止处理吗？"):
                self.stop_flag = True
                self.pause_event.set()  # 如果在暂停状态，先恢复以便退出
                self.log("⏹ 正在停止...")

    def wait_semi_decision(self, input_folder, next_index):
        """半自动模式：等待用户确认"""
        self.semi_result = None
        self.semi_new_prompt = None  # 存储新提示词
        self.semi_done_event.clear()

        # 在主线程中显示对话框
        self.root.after(0, lambda: self.show_semi_dialog(input_folder, next_index))

        # 等待用户决定（带超时，以便检查 stop_flag）
        while not self.semi_done_event.is_set():
            self.semi_done_event.wait(timeout=0.3)
            if self.stop_flag:
                self.semi_result = "stop"
                self.semi_done_event.set()
                break

        # 如果用户修改了提示词，更新主界面的提示词
        if self.semi_new_prompt is not None:
            self.prompt_text.set(self.semi_new_prompt)

        # 清理引用
        self.semi_dialog_ref = None

    def show_semi_dialog(self, input_folder, next_index):
        """显示半自动模式确认对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("生成完成 - 请选择操作")
        dialog.resizable(True, True)
        dialog.transient(self.root)
        dialog.grab_set()  # 模态对话框

        self.semi_dialog_ref = dialog

        # 计算对话框尺寸：左侧按钮+提示词 + 右侧下一张预览
        dialog_width = 820
        dialog_height = 520
        dialog.geometry(f"{dialog_width}x{dialog_height}")

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog_width // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog_height // 2)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # 标题
        tk.Label(
            dialog,
            text="图片已生成完成（下方预览区可查看结果）",
            font=("Microsoft YaHei UI", 12, "bold")
        ).pack(pady=(8, 5))

        # 提示词预设区域
        presets_frame = tk.Frame(dialog)
        presets_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        tk.Label(presets_frame, text="预设:", font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=(0, 5))

        preset_btn_frame = tk.Frame(presets_frame)
        preset_btn_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 预设按钮列表（用于动态刷新）
        preset_buttons = []

        def apply_preset(text):
            """应用预设到输入框"""
            prompt_entry.delete(0, tk.END)
            prompt_entry.insert(0, text)

        def add_preset():
            """添加当前提示词为预设"""
            current = prompt_entry.get().strip()
            if not current:
                return
            if current in self.prompt_presets:
                return
            self.prompt_presets.append(current)
            self._save_presets()
            _refresh_preset_buttons()

        def delete_last_preset():
            """删除最后一个预设"""
            if self.prompt_presets:
                self.prompt_presets.pop()
                self._save_presets()
                _refresh_preset_buttons()

        def _refresh_preset_buttons():
            """刷新预设按钮显示"""
            for btn in preset_buttons:
                btn.destroy()
            preset_buttons.clear()
            for p in self.prompt_presets:
                display = p[:12] + "..." if len(p) > 12 else p
                btn = tk.Button(
                    preset_btn_frame,
                    text=display,
                    command=lambda t=p: apply_preset(t),
                    font=("Microsoft YaHei UI", 8),
                    bg="#E3F2FD",
                    fg="#1565C0",
                    relief=tk.RAISED,
                    padx=4,
                    pady=1
                )
                btn.bind("<Button-3>", lambda e, t=p: _delete_preset(t))
                btn.pack(side=tk.LEFT, padx=1)
                preset_buttons.append(btn)

        def _delete_preset(text):
            """删除指定预设"""
            if text in self.prompt_presets:
                self.prompt_presets.remove(text)
                self._save_presets()
                _refresh_preset_buttons()

        _refresh_preset_buttons()

        # 添加/删除按钮
        tk.Button(
            presets_frame,
            text="+",
            command=add_preset,
            font=("Microsoft YaHei UI", 9, "bold"),
            width=3,
            bg="#E8F5E9",
            fg="#2E7D32"
        ).pack(side=tk.LEFT, padx=(5, 2))

        tk.Button(
            presets_frame,
            text="−",
            command=delete_last_preset,
            font=("Microsoft YaHei UI", 9, "bold"),
            width=3,
            bg="#FFEBEE",
            fg="#C62828"
        ).pack(side=tk.LEFT, padx=2)

        # 主容器：左右分栏
        main_pane = tk.Frame(dialog)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 左侧：提示词编辑 + 按钮
        left_panel = tk.Frame(main_pane)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        # 提示词编辑区域
        prompt_edit_frame = tk.LabelFrame(left_panel, text="提示词（当前即将处理的）", font=("Microsoft YaHei UI", 9))
        prompt_edit_frame.pack(fill=tk.X, pady=(0, 8))

        prompt_entry = tk.Entry(prompt_edit_frame, font=("Microsoft YaHei UI", 10))
        prompt_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8, pady=5)
        prompt_entry.insert(0, self.prompt_text.get())

        # 按钮行
        btn_frame = tk.Frame(left_panel)
        btn_frame.pack(pady=5)

        # 重新生成按钮
        retry_btn = tk.Button(
            btn_frame,
            text="↻ 不满意，重新生成",
            command=lambda: self.semi_decide("retry", dialog, prompt_entry.get()),
            width=20,
            bg="#FF9800",
            fg="white",
            font=("Microsoft YaHei UI", 10)
        )
        retry_btn.pack(side=tk.LEFT, padx=5)

        # 下一张按钮
        next_btn = tk.Button(
            btn_frame,
            text="✓ 满意，下一张",
            command=lambda: self.semi_decide("next", dialog, prompt_entry.get()),
            width=16,
            bg="#4CAF50",
            fg="white",
            font=("Microsoft YaHei UI", 10)
        )
        next_btn.pack(side=tk.LEFT, padx=5)

        # 停止按钮
        stop_btn = tk.Button(
            btn_frame,
            text="⏹ 停止",
            command=lambda: self.semi_decide("stop", dialog, prompt_entry.get()),
            width=10,
            bg="#f44336",
            fg="white",
            font=("Microsoft YaHei UI", 10)
        )
        stop_btn.pack(side=tk.LEFT, padx=5)

        # 右侧：下一张预览
        right_panel = tk.LabelFrame(main_pane, text="下一张输入预览", font=("Microsoft YaHei UI", 9))
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(8, 0))

        next_preview_label = tk.Label(right_panel, text="无更多图片", fg="#888", font=("Microsoft YaHei UI", 10))
        next_preview_label.pack(expand=True)

        # 加载下一张图片
        if next_index < len(self.image_files):
            next_image_file = self.image_files[next_index]
            next_input_path = os.path.join(input_folder, next_image_file)
            try:
                img = Image.open(next_input_path)
                # 限制预览大小
                max_w, max_h = 280, 350
                ratio = min(max_w / img.width, max_h / img.height, 1.0)
                if ratio < 1.0:
                    img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                next_preview_label.config(image=photo, text="", anchor=tk.CENTER)
                next_preview_label.image = photo  # 防止被 GC
                next_preview_label.config(text=next_image_file, compound=tk.BOTTOM)
            except Exception as e:
                next_preview_label.config(text=f"加载失败: {e}", fg="red")

        # 如果还有下张之后的图片，加个小标记
        if next_index + 1 < len(self.image_files):
            after_next = self.image_files[next_index + 1]
            info_text = f"即将: {self.image_files[next_index]}  |  之后: {after_next}"
        else:
            info_text = f"即将: {self.image_files[next_index]}  |  这是最后一张"

        tk.Label(
            left_panel,
            text=info_text,
            fg="#666",
            font=("Microsoft YaHei UI", 8)
        ).pack(pady=(8, 0), side=tk.BOTTOM)

    def semi_decide(self, decision, dialog, new_prompt=None):
        """处理用户的决定"""
        self.semi_result = decision
        # 如果提示词有变化，保存新提示词
        if new_prompt is not None and new_prompt != self.prompt_text.get():
            self.semi_new_prompt = new_prompt
        self.semi_done_event.set()
        dialog.destroy()

    def _update_button_state(self, running, paused):
        """更新按钮状态"""
        if running:
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL if not paused else tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL if not paused else tk.DISABLED)
            self.resume_button.config(state=tk.NORMAL if paused else tk.DISABLED)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

    def process_batch(self, input_folder, output_folder, image_files, start_index):
        """批量处理图片"""
        total = len(image_files)
        success_count = 0

        # 创建原图和输出图片子文件夹
        original_folder = os.path.join(output_folder, "control")
        output_image_folder = os.path.join(output_folder, "target")
        os.makedirs(original_folder, exist_ok=True)
        os.makedirs(output_image_folder, exist_ok=True)

        # 检查是否为半自动模式
        is_semi_auto = self.process_mode.get() == "半自动模式"

        # 从指定索引开始处理
        i = start_index
        while i < len(image_files):
            # 检查是否被停止
            if self.stop_flag:
                self.root.after(0, lambda: self.log("⏹ 处理已停止"))
                break

            # 检查是否被暂停，等待继续
            while self.is_paused:
                time.sleep(0.5)
                if self.stop_flag:
                    break

            # 每次循环前获取最新的提示词和 LoRA 路径（支持在半自动模式下修改）
            prompt = self.prompt_text.get().strip()
            lora_name = self.lora_path.get().strip()
            resize_value = self.resize_longest_edge.get()

            image_file = image_files[i]
            # 更新当前索引
            self.current_index = i
            # 更新进度
            progress = (i + 1) / total * 100
            input_path = os.path.join(input_folder, image_file)

            self.root.after(0, lambda p=progress, f=image_file, idx=i, t=total: self.update_progress(p, f, idx, t))

            # 处理图片
            workflow = self.processor.load_workflow()
            success, result = self.processor.process_image(
                workflow, input_path, output_folder, original_folder,
                output_image_folder, prompt, lora_name, resize_value
            )

            if success:
                success_count += 1
                self.root.after(0, lambda f=image_file, r=result: self.log(f"✓ {f} -> {r}"))
                # 生成完成时才同时更新输入图和输出图预览，确保配对正确
                self.root.after(0, lambda inp=input_path, out=result: self.update_both_previews(inp, out))

                # 半自动模式下等待用户确认
                if is_semi_auto:
                    next_idx = i + 1
                    self.root.after(0, lambda: self.log("⏸ 等待用户确认..."))
                    self.wait_semi_decision(input_folder, next_idx)

                    # 检查用户决定
                    if self.semi_result == "stop":
                        self.start_index.set(self.current_index)
                        self.root.after(0, lambda: self.log("⏹ 处理已停止"))
                        break
                    elif self.semi_result == "retry":
                        # 重新生成，不增加索引（提示词已在 wait_semi_decision 中更新）
                        self.root.after(0, lambda: self.log("↻ 重新生成当前图片..."))
                        continue
                    elif self.semi_result == "next":
                        # 下一张
                        i += 1
                        continue
            else:
                self.root.after(0, lambda f=image_file, r=result: self.log(f"✗ {f} - {r}"))
                # 失败时也等待用户确认
                if is_semi_auto:
                    next_idx = i + 1
                    self.root.after(0, lambda: self.log("⏸ 等待用户确认..."))
                    self.wait_semi_decision(input_folder, next_idx)

                    if self.semi_result == "stop":
                        self.start_index.set(self.current_index)
                        break
                    elif self.semi_result == "retry":
                        continue
                    elif self.semi_result == "next":
                        i += 1
                        continue
                else:
                    i += 1
                    continue

            i += 1

        self.root.after(0, lambda sc=success_count, t=total, si=start_index: self.finish_processing(sc, t, si))

    def update_progress(self, progress, filename, current, total):
        """更新进度显示"""
        self.progress['value'] = progress
        self.progress_label.config(text=f"处理中：{current + 1}/{total} - {filename}")

    def finish_processing(self, success_count, total, start_index=0):
        """处理完成"""
        self.is_running = False
        self.is_paused = False
        self._update_button_state(False, False)

        # 重新启用起始索引输入框
        self.start_index_spinbox.config(state=tk.NORMAL)

        if self.stop_flag:
            # 停止时，将起始索引设置为当前索引，方便下次从暂停位置继续
            self.start_index.set(self.current_index)
            self.progress_label.config(text=f"已停止！{self.current_index + 1}/{total}")
            self.log(f"⏹ 处理已停止，成功：{success_count}, 下次可从第 {self.current_index} 个重新开始")
        else:
            self.progress_label.config(text=f"完成！{total}/{total}")
            messagebox.showinfo("完成", f"批量处理完成!\n成功：{success_count}\n失败：{total - success_count - start_index}")


def main():
    """主函数"""
    root = tk.Tk()
    app = BatchProcessorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()