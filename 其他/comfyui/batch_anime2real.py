#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ComfyUI 批量动漫转写实处理脚本 - GUI 版本
使用方法：直接运行，通过图形界面选择文件夹
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import requests
import uuid
import time
import os
from pathlib import Path
import threading


class ComfyUIBatchProcessor:
    """ComfyUI 批量处理器"""
    
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.workflow_path = r"J:\Ai_visual_processing_tools\其他\comfyui\动漫转写实真人2511（AnythingtoRealCharacters）正式版-高还原.json"
        
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
    
    def process_image(self, workflow, input_image_path, output_folder):
        """处理单张图片"""
        # 修改 LoadImage 节点的输入图片
        workflow["78"]["inputs"]["image"] = input_image_path
        
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
                            # 生成输出文件名
                            output_name = f"{Path(input_image_path).stem}_real.png"
                            output_path = os.path.join(output_folder, output_name)
                            with open(output_path, 'wb') as f:
                                f.write(img_data)
                            return True, output_path
            time.sleep(1)
        
        return False, "任务超时"


class BatchProcessorGUI:
    """批量处理 GUI 界面"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("ComfyUI 批量动漫转写实处理")
        self.root.geometry("600x400")
        
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.processor = ComfyUIBatchProcessor()
        
        self.create_widgets()
    
    def create_widgets(self):
        """创建界面组件"""
        # 输入文件夹选择
        input_frame = tk.Frame(self.root, pady=10)
        input_frame.pack(fill=tk.X, padx=20)
        tk.Label(input_frame, text="输入文件夹:", width=12).pack(side=tk.LEFT)
        tk.Entry(input_frame, textvariable=self.input_folder, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(input_frame, text="浏览", command=self.select_input_folder).pack(side=tk.LEFT)
        
        # 输出文件夹选择
        output_frame = tk.Frame(self.root, pady=10)
        output_frame.pack(fill=tk.X, padx=20)
        tk.Label(output_frame, text="输出文件夹:", width=12).pack(side=tk.LEFT)
        tk.Entry(output_frame, textvariable=self.output_folder, width=40).pack(side=tk.LEFT, padx=5)
        tk.Button(output_frame, text="浏览", command=self.select_output_folder).pack(side=tk.LEFT)
        
        # 进度条
        progress_frame = tk.Frame(self.root, pady=10)
        progress_frame.pack(fill=tk.X, padx=20)
        self.progress = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress.pack(fill=tk.X)
        self.progress_label = tk.Label(progress_frame, text="")
        self.progress_label.pack()
        
        # 开始按钮
        button_frame = tk.Frame(self.root, pady=20)
        button_frame.pack()
        self.start_button = tk.Button(button_frame, text="开始处理", command=self.start_processing, width=20)
        self.start_button.pack()
        
        # 日志区域
        log_frame = tk.Frame(self.root, pady=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        tk.Label(log_frame, text="处理日志:").pack(anchor=tk.W)
        self.log_text = tk.Text(log_frame, height=8, width=60)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
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
        image_files = [f for f in os.listdir(input_folder) 
                      if Path(f).suffix.lower() in image_extensions]
        
        if not image_files:
            messagebox.showwarning("警告", "输入文件夹中没有找到图片文件")
            return
        
        # 禁用按钮，启动线程处理
        self.start_button.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.process_batch, 
                                 args=(input_folder, output_folder, image_files))
        thread.start()
    
    def process_batch(self, input_folder, output_folder, image_files):
        """批量处理图片"""
        total = len(image_files)
        success_count = 0
        
        for i, image_file in enumerate(image_files):
            # 更新进度
            progress = (i + 1) / total * 100
            self.root.after(0, lambda p=progress, f=image_file: self.update_progress(p, f))
            
            # 处理图片
            input_path = os.path.join(input_folder, image_file)
            workflow = self.processor.load_workflow()
            success, result = self.processor.process_image(workflow, input_path, output_folder)
            
            if success:
                success_count += 1
                self.root.after(0, lambda f=image_file, r=result: self.log(f"✓ {f} -> {r}"))
            else:
                self.root.after(0, lambda f=image_file, r=result: self.log(f"✗ {f} - {r}"))
        
        self.root.after(0, lambda: self.finish_processing(success_count, total))
    
    def update_progress(self, progress, filename):
        """更新进度显示"""
        self.progress['value'] = progress
        self.progress_label.config(text=f"处理中：{filename}")
    
    def finish_processing(self, success_count, total):
        """处理完成"""
        self.start_button.config(state=tk.NORMAL)
        self.progress_label.config(text=f"完成！成功：{success_count}/{total}")
        messagebox.showinfo("完成", f"批量处理完成!\n成功：{success_count}\n失败：{total - success_count}")


def main():
    """主函数"""
    root = tk.Tk()
    app = BatchProcessorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()