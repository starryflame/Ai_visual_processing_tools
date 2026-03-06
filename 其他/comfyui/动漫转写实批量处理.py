import json
import requests
import time
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from datetime import datetime

class AnimeToRealBatchProcessor:
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address
        self.client_id = str(time.time())
        self.processed_count = 0
        self.total_count = 0
        self.is_running = False
        
    def queue_prompt(self, prompt):
        """向ComfyUI队列发送提示"""
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        try:
            response = requests.post(f"http://{self.server_address}/prompt", data=data, timeout=30)
            return response.json()
        except Exception as e:
            print(f"发送请求失败: {str(e)}")
            return None
            
    def get_history(self, prompt_id):
        """获取历史记录"""
        try:
            response = requests.get(f"http://{self.server_address}/history/{prompt_id}", timeout=10)
            return response.json()
        except Exception as e:
            print(f"获取历史记录失败: {str(e)}")
            return {}
            
    def load_workflow(self, workflow_path):
        """加载工作流JSON文件"""
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载工作流文件失败: {str(e)}")
            return None
            
    def update_image_input(self, workflow_json, image_path):
        """更新工作流中的图片输入路径"""
        # 查找LoadImage节点（节点78）
        node_id = "78"
        if node_id in workflow_json:
            if workflow_json[node_id]['class_type'] == 'LoadImage':
                # 更新图片路径
                workflow_json[node_id]['inputs']['image'] = image_path
                print(f"已设置图片输入: {image_path}")
                return True
        else:
            # 如果找不到节点78，尝试查找其他LoadImage节点
            for node_id, node in workflow_json.items():
                if node['class_type'] == 'LoadImage':
                    node['inputs']['image'] = image_path
                    print(f"已设置图片输入到节点 {node_id}: {image_path}")
                    return True
                    
        print("警告：未找到LoadImage节点")
        return False
        
    def update_output_settings(self, workflow_json, output_prefix):
        """更新输出设置"""
        # 查找SaveImage节点（节点189）
        node_id = "189"
        if node_id in workflow_json:
            if workflow_json[node_id]['class_type'] == 'SaveImage':
                workflow_json[node_id]['inputs']['filename_prefix'] = output_prefix
                print(f"已设置输出前缀: {output_prefix}")
                return True
        else:
            # 如果找不到节点189，尝试查找其他SaveImage节点
            for node_id, node in workflow_json.items():
                if node['class_type'] == 'SaveImage':
                    node['inputs']['filename_prefix'] = output_prefix
                    print(f"已设置输出前缀到节点 {node_id}: {output_prefix}")
                    return True
                    
        print("警告：未找到SaveImage节点")
        return False
        
    def process_single_image(self, image_path, output_prefix, workflow_path):
        """处理单张图片"""
        # 加载工作流
        workflow = self.load_workflow(workflow_path)
        if not workflow:
            return False
            
        # 更新输入图片路径
        if not self.update_image_input(workflow, image_path):
            return False
            
        # 更新输出设置
        if not self.update_output_settings(workflow, output_prefix):
            return False
            
        # 发送工作流到ComfyUI
        try:
            response = self.queue_prompt(workflow)
            if not response or 'prompt_id' not in response:
                print(f"提交任务失败: {response}")
                return False
                
            prompt_id = response['prompt_id']
            print(f"已提交任务: {prompt_id}")
            
        except Exception as e:
            print(f"提交任务失败: {str(e)}")
            return False
            
        # 等待处理完成
        max_wait_time = 300  # 最大等待5分钟
        start_time = time.time()
        
        while True:
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    if 'status' in prompt_data and prompt_data['status'].get('completed', False):
                        print(f"图片处理完成: {image_path}")
                        return True
                    elif time.time() - start_time > max_wait_time:
                        print(f"任务超时 ({max_wait_time}秒): {image_path}")
                        return False
                        
            except Exception as e:
                print(f"获取任务状态失败: {str(e)}")
                if time.time() - start_time > max_wait_time:
                    return False
                    
            time.sleep(2)  # 等待2秒后检查
            
        return False
        
    def get_all_image_files(self, input_path, extensions=('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
        """递归获取所有图片文件"""
        image_files = []
        input_path = Path(input_path)
        
        for ext in extensions:
            image_files.extend(input_path.rglob(f"*{ext}"))
            image_files.extend(input_path.rglob(f"*{ext.upper()}"))
            
        # 去除重复项并排序
        image_files = sorted(list(set(image_files)))
        return image_files
        
    def batch_process(self, input_folder, workflow_path, output_folder=None):
        """批量处理图片"""
        if not self.is_running:
            return
            
        input_path = Path(input_folder)
        
        # 获取所有图片文件
        image_files = self.get_all_image_files(input_path)
        
        if not image_files:
            print(f"在 {input_folder} 及其子文件夹中没有找到图片文件")
            return
            
        self.total_count = len(image_files)
        print(f"找到 {self.total_count} 个图片文件")
        
        # 处理每个图片
        success_count = 0
        for i, image_file in enumerate(image_files):
            if not self.is_running:
                print("处理已被停止")
                break
                
            print(f"\n处理第 {i+1}/{self.total_count} 个图片: {image_file}")
            
            # 生成输出前缀
            relative_path = image_file.relative_to(input_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"{relative_path.parent / relative_path.stem}_realistic_{timestamp}"
            
            # 构造输出前缀
            if output_folder:
                # 使用自定义输出文件夹结构
                output_prefix = str(Path(output_folder) / base_name)
            else:
                # 使用默认输出前缀
                output_prefix = f"anima2real/{base_name}"
            
            try:
                result = self.process_single_image(
                    image_path=str(image_file),
                    output_prefix=output_prefix,
                    workflow_path=workflow_path
                )
                
                if result:
                    success_count += 1
                    print(f"✓ 图片 {image_file.name} 处理成功")
                else:
                    print(f"✗ 图片 {image_file.name} 处理失败")
                    
            except Exception as e:
                print(f"处理图片 {image_file.name} 时出错: {str(e)}")
                continue
                
            # 更新进度
            self.processed_count = i + 1
            
        print(f"\n批量处理完成!")
        print(f"总处理数: {self.total_count}")
        print(f"成功处理: {success_count}")
        print(f"失败数量: {self.total_count - success_count}")

class BatchProcessorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("动漫转写实批量处理器")
        self.root.geometry("600x500")
        
        # 处理器实例
        self.processor = AnimeToRealBatchProcessor()
        self.process_thread = None
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = tk.Label(main_frame, text="动漫转写实批量处理器", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 服务器地址设置
        server_frame = tk.Frame(main_frame)
        server_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(server_frame, text="ComfyUI服务器地址:", font=("Arial", 10)).pack(anchor=tk.W)
        self.server_entry = tk.Entry(server_frame, font=("Arial", 10))
        self.server_entry.insert(0, "127.0.0.1:8188")
        self.server_entry.pack(fill=tk.X, pady=(5, 0))
        
        # 输入文件夹选择
        input_frame = tk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(input_frame, text="输入文件夹 (包含动漫图片):", font=("Arial", 10)).pack(anchor=tk.W)
        
        input_select_frame = tk.Frame(input_frame)
        input_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.input_path_var = tk.StringVar()
        tk.Entry(input_select_frame, textvariable=self.input_path_var, 
                state="readonly", font=("Arial", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(input_select_frame, text="浏览", command=self.select_input_folder,
                 font=("Arial", 9)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 输出文件夹选择
        output_frame = tk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(output_frame, text="输出文件夹 (可选，默认使用ComfyUI输出目录):", 
                font=("Arial", 10)).pack(anchor=tk.W)
        
        output_select_frame = tk.Frame(output_frame)
        output_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.output_path_var = tk.StringVar()
        tk.Entry(output_select_frame, textvariable=self.output_path_var, 
                state="readonly", font=("Arial", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(output_select_frame, text="浏览", command=self.select_output_folder,
                 font=("Arial", 9)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 工作流文件选择
        workflow_frame = tk.Frame(main_frame)
        workflow_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(workflow_frame, text="工作流文件:", font=("Arial", 10)).pack(anchor=tk.W)
        
        workflow_select_frame = tk.Frame(workflow_frame)
        workflow_select_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.workflow_path_var = tk.StringVar(value=r"其他\comfyui\动漫转写实真人2511（AnythingtoRealCharacters）正式版-高还原.json")
        tk.Entry(workflow_select_frame, textvariable=self.workflow_path_var, 
                state="readonly", font=("Arial", 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Button(workflow_select_frame, text="浏览", command=self.select_workflow_file,
                 font=("Arial", 9)).pack(side=tk.RIGHT, padx=(5, 0))
        
        # 控制按钮
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.start_button = tk.Button(button_frame, text="开始处理", command=self.start_processing,
                                     bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                                     height=2)
        self.start_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.stop_button = tk.Button(button_frame, text="停止处理", command=self.stop_processing,
                                    bg="#f44336", fg="white", font=("Arial", 11, "bold"),
                                    height=2, state="disabled")
        self.stop_button.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 进度显示
        progress_frame = tk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_label = tk.Label(progress_frame, text="准备就绪", font=("Arial", 10))
        self.progress_label.pack()
        
        self.progress_var = tk.StringVar(value="进度: 0/0")
        self.progress_text = tk.Label(progress_frame, textvariable=self.progress_var, 
                                     font=("Arial", 10))
        self.progress_text.pack()
        
        # 日志显示
        log_frame = tk.Frame(main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(log_frame, text="处理日志:", font=("Arial", 10)).pack(anchor=tk.W)
        
        self.log_text = tk.Text(log_frame, height=10, font=("Consolas", 9))
        log_scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 重定向print输出到日志框
        import sys
        class StdoutRedirector:
            def __init__(self, text_widget):
                self.text_widget = text_widget
                
            def write(self, str):
                self.text_widget.insert(tk.END, str)
                self.text_widget.see(tk.END)
                
            def flush(self):
                pass
                
        sys.stdout = StdoutRedirector(self.log_text)
        
    def select_input_folder(self):
        folder = filedialog.askdirectory(title="选择包含动漫图片的文件夹")
        if folder:
            self.input_path_var.set(folder)
            
    def select_output_folder(self):
        folder = filedialog.askdirectory(title="选择输出文件夹（可选）")
        if folder:
            self.output_path_var.set(folder)
            
    def select_workflow_file(self):
        file = filedialog.askopenfilename(
            title="选择工作流文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file:
            self.workflow_path_var.set(file)
            
    def update_progress(self):
        """更新进度显示"""
        if hasattr(self.processor, 'processed_count') and hasattr(self.processor, 'total_count'):
            self.progress_var.set(f"进度: {self.processor.processed_count}/{self.processor.total_count}")
            
        # 每500ms更新一次进度
        if self.processor.is_running:
            self.root.after(500, self.update_progress)
            
    def start_processing(self):
        # 检查必要参数
        input_folder = self.input_path_var.get()
        workflow_path = self.workflow_path_var.get()
        output_folder = self.output_path_var.get() or None
        server_address = self.server_entry.get()
        
        if not input_folder:
            messagebox.showerror("错误", "请选择输入文件夹")
            return
            
        if not os.path.exists(input_folder):
            messagebox.showerror("错误", "输入文件夹不存在")
            return
            
        if not workflow_path:
            messagebox.showerror("错误", "请选择工作流文件")
            return
            
        if not os.path.exists(workflow_path):
            messagebox.showerror("错误", "工作流文件不存在")
            return
            
        # 更新处理器的服务器地址
        self.processor.server_address = server_address
        
        # 开始处理
        self.processor.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_label.config(text="正在处理中...")
        
        # 启动处理线程
        self.process_thread = threading.Thread(
            target=self.processor.batch_process,
            args=(input_folder, workflow_path, output_folder),
            daemon=True
        )
        self.process_thread.start()
        
        # 开始进度更新
        self.update_progress()
        
        # 监控线程结束
        self.monitor_thread()
        
    def stop_processing(self):
        self.processor.is_running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.progress_label.config(text="处理已停止")
        
    def monitor_thread(self):
        """监控处理线程状态"""
        if self.process_thread and self.process_thread.is_alive():
            self.root.after(1000, self.monitor_thread)
        else:
            # 处理完成
            self.processor.is_running = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            self.progress_label.config(text="处理完成")
            
    def run(self):
        self.root.mainloop()

def main():
    app = BatchProcessorGUI()
    app.run()

if __name__ == "__main__":
    main()