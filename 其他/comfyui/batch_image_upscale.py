#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 批量 WAN 图片放大处理脚本 - GUI 版本
基于 wan_图片放大工作流
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import requests
import time
import os
from pathlib import Path
import threading


class ComfyUISeedVR2UpscaleProcessor:
    """ComfyUI SeedVR2 图片放大处理器"""

    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.workflow_path = r"J:\Ai_visual_processing_tools\其他\comfyui\工作流\seedvr2uoscale.json"

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

    def process_image(self, workflow, input_image_path, output_folder,
                      seed, max_resolution, min_resolution, longer_edge,
                      vae_model, dit_model):
        """处理单张图片"""
        # 修改 LoadImage 节点的输入图片 (节点 9)
        workflow["9"]["inputs"]["image"] = input_image_path

        # 修改缩放参数 (节点 17)
        workflow["17"]["inputs"]["longer_edge"] = longer_edge

        # 修改最小分辨率 (节点 3)
        workflow["3"]["inputs"]["value"] = min_resolution

        # 修改最大分辨率 (节点 2)
        workflow["2"]["inputs"]["value"] = max_resolution

        # 修改 Seed 参数 (节点 8)
        workflow["8"]["inputs"]["seed"] = seed

        # 修改 VAE 模型路径 (节点 1)
        workflow["1"]["inputs"]["model"] = vae_model

        # 修改 DiT 模型路径 (节点 4)
        workflow["4"]["inputs"]["model"] = dit_model

        # 提交任务
        result = self.queue_prompt(workflow)
        if "prompt_id" not in result:
            return False, "任务提交失败"

        prompt_id = result["prompt_id"]

        # 等待任务完成
        max_wait = 600  # 最大等待 10 分钟
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
                            # 生成输出文件名 - 保持原文件名
                            output_name = f"{Path(input_image_path).name}"
                            output_path = os.path.join(output_folder, output_name)
                            with open(output_path, 'wb') as f:
                                f.write(img_data)
                            return True, output_path
            time.sleep(1)

        return False, "任务超时"


class BatchSeedVR2UpscaleGUI:
    """批量 SeedVR2 图片放大 GUI 界面"""

    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI SeedVR2 图片批量放大")
        self.root.geometry("900x700")

        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.processor = ComfyUISeedVR2UpscaleProcessor()

        # 参数变量
        self.seed = tk.IntVar(value=863109500)
        self.max_resolution = tk.IntVar(value=4096)
        self.min_resolution = tk.IntVar(value=4096)
        self.longer_edge = tk.IntVar(value=512)

        # 模型路径变量
        self.vae_model = tk.StringVar(value=r"ema_vae_fp16.safetensors")
        self.dit_model = tk.StringVar(value=r"seedvr2_ema_3b_fp8_e4m3fn.safetensors")

        # 控制变量
        self.is_running = False
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.stop_flag = False
        self.image_files = []
        self.current_index = 0
        self.total_count = 0

        # 日志区折叠状态
        self.log_expanded = True

        # 控制面板隐藏状态
        self.control_panel_hidden = False

        self.create_widgets()

        # 绑定 ESC 键退出全屏
        self.root.bind('<Escape>', lambda _: self.toggle_fullscreen())
        # 绑定 F11 切换全屏
        self.root.bind('<F11>', lambda _: self.toggle_fullscreen())
        # 绑定 Tab 键隐藏控制面板
        self.root.bind('<Tab>', lambda _: self.toggle_control_panel())

    def create_widgets(self):
        """创建界面组件"""
        # 主容器 - 上下分栏
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 上部 - 控制面板
        self.control_frame = tk.Frame(main_container)
        self.control_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)

        # 下部 - 日志区
        log_frame = tk.Frame(main_container, bg='#1a1a1a', relief=tk.RAISED, bd=2)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.create_control_panel(self.control_frame)
        self.create_log_panel(log_frame)

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
        """创建控制面板"""
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

        # 分隔线
        separator1 = ttk.Separator(parent, orient='horizontal')
        separator1.pack(fill=tk.X, pady=5)

        # 放大参数区域 - 使用 LabelFrame
        params_frame = tk.LabelFrame(parent, text="放大参数", padx=10, pady=10)
        params_frame.pack(fill=tk.X, pady=5)

        # 第一行：Seed
        row1 = tk.Frame(params_frame)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="Seed:", width=10).pack(side=tk.LEFT)
        tk.Spinbox(row1, textvariable=self.seed, from_=0, to=999999999999999, width=15).pack(side=tk.LEFT, padx=5)

        # 第二行：最大/最小分辨率
        row2 = tk.Frame(params_frame)
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="最大分辨率:", width=10).pack(side=tk.LEFT)
        tk.Spinbox(row2, textvariable=self.max_resolution, from_=256, to=8192, increment=256, width=10).pack(side=tk.LEFT, padx=5)
        tk.Label(row2, text="最小分辨率:", width=8).pack(side=tk.LEFT, padx=(20, 0))
        tk.Spinbox(row2, textvariable=self.min_resolution, from_=256, to=8192, increment=256, width=10).pack(side=tk.LEFT, padx=5)

        # 第三行：缩放长度
        row3 = tk.Frame(params_frame)
        row3.pack(fill=tk.X, pady=2)
        tk.Label(row3, text="长边缩放:", width=10).pack(side=tk.LEFT)
        tk.Spinbox(row3, textvariable=self.longer_edge, from_=256, to=4096, increment=64, width=10).pack(side=tk.LEFT, padx=5)
        tk.Label(row3, text="(ResizeImagesByLongerEdge 参数)", fg="#666").pack(side=tk.LEFT, padx=5)

        # 分隔线
        separator2 = ttk.Separator(parent, orient='horizontal')
        separator2.pack(fill=tk.X, pady=5)

        # 模型路径区域 - 可折叠
        self.model_frame = tk.LabelFrame(parent, text="模型路径", padx=10, pady=10)
        self.model_frame.pack(fill=tk.X, pady=5)

        # VAE 模型路径
        vae_row = tk.Frame(self.model_frame)
        vae_row.pack(fill=tk.X, pady=2)
        tk.Label(vae_row, text="VAE 模型:", width=10).pack(side=tk.LEFT)
        tk.Entry(vae_row, textvariable=self.vae_model).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # DiT 模型路径
        dit_row = tk.Frame(self.model_frame)
        dit_row.pack(fill=tk.X, pady=2)
        tk.Label(dit_row, text="DiT 模型:", width=10).pack(side=tk.LEFT)
        tk.Entry(dit_row, textvariable=self.dit_model).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 分隔线
        separator3 = ttk.Separator(parent, orient='horizontal')
        separator3.pack(fill=tk.X, pady=5)

        # 起始索引
        index_frame = tk.Frame(parent, pady=5)
        index_frame.pack(fill=tk.X)
        tk.Label(index_frame, text="从第几个开始:", width=12).pack(side=tk.LEFT)
        self.start_index = tk.IntVar(value=0)
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

        # 日志区域
        log_container = tk.Frame(parent, pady=10)
        log_container.pack(fill=tk.BOTH, expand=True)

        # 日志标题栏
        log_header_frame = tk.Frame(log_container)
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

        # 日志文本区域
        self.log_container_frame = tk.Frame(log_container)
        self.log_container_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(self.log_container_frame, height=8, width=60)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def create_log_panel(self, parent):
        """创建日志面板（占位，实际日志在控制面板下方）"""
        # 这个方法被单独调用时的备用方案
        pass

    def toggle_fullscreen(self):
        """切换全屏模式"""
        current = self.root.attributes('-fullscreen')
        self.root.attributes('-fullscreen', not current)

        if not current:
            self.fullscreen_hint.pack_forget()
        else:
            self.fullscreen_hint.pack(anchor=tk.W, padx=10, pady=(0, 5))

    def toggle_control_panel(self):
        """切换控制面板显示/隐藏"""
        if self.control_panel_hidden:
            self.control_frame.pack(fill=tk.X, expand=False, padx=10, pady=10)
            self.control_panel_hidden = False
        else:
            self.control_frame.pack_forget()
            self.control_panel_hidden = True

    def toggle_log(self):
        """切换日志区显示/隐藏"""
        if self.log_expanded:
            self.log_container_frame.pack_forget()
            self.log_toggle_button.config(text="▼ 展开")
            self.log_expanded = False
        else:
            self.log_container_frame.pack(fill=tk.BOTH, expand=True)
            self.log_toggle_button.config(text="▲ 收起")
            self.log_expanded = True

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
                self.pause_event.set()
                self.log("⏹ 正在停止...")

    def process_batch(self, input_folder, output_folder, image_files, start_index):
        """批量处理图片"""
        success_count = 0

        # 获取参数
        seed = self.seed.get()
        max_resolution = self.max_resolution.get()
        min_resolution = self.min_resolution.get()
        longer_edge = self.longer_edge.get()

        vae_model = self.vae_model.get().strip()
        dit_model = self.dit_model.get().strip()

        for i in range(start_index, len(image_files)):
            if self.stop_flag:
                self.root.after(0, lambda: self.log("⏹ 处理已停止"))
                break

            while self.is_paused:
                time.sleep(0.5)
                if self.stop_flag:
                    break

            image_file = image_files[i]
            self.current_index = i
            progress = (i + 1) / self.total_count * 100
            input_path = os.path.join(input_folder, image_file)

            self.root.after(0, lambda p=progress, f=image_file, idx=i, t=self.total_count: self.update_progress(p, f, idx, t))

            workflow = self.processor.load_workflow()
            success, result = self.processor.process_image(
                workflow, input_path, output_folder,
                seed, max_resolution, min_resolution, longer_edge,
                vae_model, dit_model
            )

            if success:
                success_count += 1
                self.root.after(0, lambda f=image_file, r=result: self.log(f"✓ {f} -> {r}"))
            else:
                self.root.after(0, lambda f=image_file, r=result: self.log(f"✗ {f} - {r}"))

        self.root.after(0, lambda sc=success_count, t=self.total_count, si=start_index: self.finish_processing(sc, t, si))

    def update_progress(self, progress, filename, current, total):
        """更新进度显示"""
        self.progress['value'] = progress
        self.progress_label.config(text=f"处理中：{current + 1}/{total} - {filename}")

    def finish_processing(self, success_count, total, start_index=0):
        """处理完成"""
        self.is_running = False
        self.is_paused = False

        # 更新按钮状态
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)

        # 重新启用起始索引输入框
        self.start_index_spinbox.config(state=tk.NORMAL)

        if self.stop_flag:
            self.start_index.set(self.current_index)
            self.progress_label.config(text=f"已停止！{self.current_index + 1}/{total}")
            self.log(f"⏹ 处理已停止，成功：{success_count}, 下次可从第 {self.current_index} 个重新开始")
        else:
            self.progress_label.config(text=f"完成！{total}/{total}")
            failed = total - success_count - start_index
            messagebox.showinfo("完成", f"批量处理完成!\n成功：{success_count}\n失败：{failed}")


def main():
    """主函数"""
    root = tk.Tk()
    app = BatchSeedVR2UpscaleGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
