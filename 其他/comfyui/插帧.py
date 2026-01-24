import json
import requests
import time
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

class ComfyUIBatchProcessor:
    def __init__(self, server_address="127.0.0.1:8189"):
        self.server_address = server_address
        self.client_id = str(time.time())

    def queue_prompt(self, prompt):
        """向ComfyUI队列发送提示"""
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        response = requests.post(f"http://{self.server_address}/prompt", data=data)
        return response.json()

    def get_image(self, filename, subfolder, folder_type):
        """获取图像数据"""
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = json.dumps(data)
        with requests.get(f"http://{self.server_address}/view?{url_values}") as response:
            return response.content

    def get_history(self, prompt_id):
        """获取历史记录"""
        response = requests.get(f"http://{self.server_address}/history/{prompt_id}")
        return response.json()

    def load_workflow(self, workflow_path):
        """加载工作流JSON文件"""
        with open(workflow_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def update_video_input(self, workflow_json, video_path):
        """更新工作流中的视频输入路径"""
        for node_id, node in workflow_json.items():
            if node['class_type'] == 'VHS_LoadVideo':
                node['inputs']['video'] = video_path
                print(f"已设置视频输入: {video_path}")
                break

    def update_output_settings(self, workflow_json, output_prefix):
        """更新输出设置"""
        for node_id, node in workflow_json.items():
            if node['class_type'] == 'VHS_VideoCombine':
                node['inputs']['filename_prefix'] = output_prefix
                print(f"已设置输出前缀: {output_prefix}")
                break

    def process_video(self, input_video_path, output_prefix, workflow_path):
        """处理单个视频"""
        # 加载并修改工作流
        workflow = self.load_workflow(workflow_path)
        self.update_video_input(workflow, input_video_path)
        self.update_output_settings(workflow, output_prefix)

        # 发送工作流到ComfyUI
        try:
            response = self.queue_prompt(workflow)
            prompt_id = response['prompt_id']
            print(f"已提交任务: {prompt_id}")
        except Exception as e:
            print(f"提交任务失败: {str(e)}")
            return False

        # 等待处理完成
        status = None
        while status is None or status.get('status_str') != 'success':
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history and 'status' in history[prompt_id] and history[prompt_id]['status']['completed']:
                    status = history[prompt_id]['status']
                    break
            except Exception as e:
                print(f"获取任务状态失败: {str(e)}")
                time.sleep(2)
                continue
            time.sleep(2)  # 等待2秒后检查

        print(f"视频处理完成: {input_video_path} -> {output_prefix}")
        return True

    def batch_process(self, input_folder, workflow_path, extensions=('.mp4', '.mov', '.avi', '.mkv')):
        """批量处理视频"""
        input_path = Path(input_folder)

        # 获取所有视频文件
        video_files = []
        for ext in extensions:
            video_files.extend(input_path.glob(f"*{ext}"))

        # 去除可能的重复项
        video_files = list(set(video_files))

        if not video_files:
            print(f"在 {input_folder} 中没有找到视频文件")
            return

        print(f"找到 {len(video_files)} 个视频文件")

        # 处理每个视频
        for i, video_file in enumerate(video_files):
            print(f"\n处理第 {i+1}/{len(video_files)} 个视频: {video_file.name}")
            
            output_prefix = f"{video_file.stem}_interpolated_{i+1:03d}"
            
            try:
                result = self.process_video(
                    input_video_path=str(video_file),
                    output_prefix=output_prefix,
                    workflow_path=workflow_path
                )
                
                if result:
                    print(f"✓ 视频 {video_file.name} 处理成功")
                else:
                    print(f"✗ 视频 {video_file.name} 处理失败")
                    
            except Exception as e:
                print(f"处理视频 {video_file.name} 时出错: {str(e)}")
                continue

def main():
    # 创建tkinter根窗口并隐藏它
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 让用户选择包含视频的文件夹
    INPUT_FOLDER = filedialog.askdirectory(title="选择包含视频的文件夹")
    
    # 如果用户取消了选择，则退出程序
    if not INPUT_FOLDER:
        print("未选择文件夹，程序退出")
        return
    
    WORKFLOW_PATH = r"j:\Data\Ai_visual_processing_tools\其他\comfyui\视频插帧.json"
    
    # 检查输入文件夹是否存在
    if not os.path.exists(INPUT_FOLDER):
        print(f"输入文件夹不存在: {INPUT_FOLDER}")
        return
        
    # 检查工作流文件是否存在
    if not os.path.exists(WORKFLOW_PATH):
        print(f"工作流文件不存在: {WORKFLOW_PATH}")
        return
    
    print("开始批量处理视频...")
    print(f"输入文件夹: {INPUT_FOLDER}")
    print(f"工作流文件: {WORKFLOW_PATH}")
    
    # 创建处理器实例
    processor = ComfyUIBatchProcessor(server_address="127.0.0.1:8189")  # 修改为您的ComfyUI服务器地址
    
    # 批量处理视频
    processor.batch_process(INPUT_FOLDER, WORKFLOW_PATH)

if __name__ == "__main__":
    main()