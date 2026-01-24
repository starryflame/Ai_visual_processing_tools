import json
import requests
import time
import uuid
import os
import tkinter as tk
from tkinter import filedialog
class ComfyUIClient:
    def __init__(self, server_address="127.0.0.1:8189"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, prompt):
        """将提示词发送到队列"""
        p = {"prompt": prompt, "client_id": self.client_id}
        data = json.dumps(p).encode('utf-8')
        req = requests.post(f"http://{self.server_address}/prompt", data=data)
        return req.json()

    def get_image(self, filename, subfolder, folder_type):
        """获取图像"""
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url_values = json.dumps(data)
        with requests.get(f"http://{self.server_address}/view?{url_values}") as response:
            return response.content

    def get_history(self, prompt_id):
        """获取历史记录"""
        resp = requests.get(f"http://{self.server_address}/history/{prompt_id}")
        return resp.json()

    def load_workflow(self, workflow_path):
        """加载工作流配置"""
        with open(workflow_path, 'r', encoding='utf-8') as f:
            workflow = json.load(f)
        return workflow

    def update_video_input(self, workflow, video_path, node_id="22"):
        """更新视频输入节点"""
        if node_id in workflow:
            workflow[node_id]["inputs"]["video"] = video_path
        else:
            print(f"警告：节点 {node_id} 不存在于工作流中")

    def update_output_settings(self, workflow, output_prefix="processed_video", node_id="21"):
        """更新输出设置"""
        if node_id in workflow:
            workflow[node_id]["inputs"]["filename_prefix"] = output_prefix
        else:
            print(f"警告：节点 {node_id} 不存在于工作流中")

    def process_video(self, input_video_path, output_prefix="processed_video"):
        """处理单个视频"""
        # 加载原始工作流
        workflow = self.load_workflow(r"其他\comfyui\wan视频放大.json")
        
        # 更新视频输入
        self.update_video_input(workflow, input_video_path)
        
        # 更新输出设置
        self.update_output_settings(workflow, output_prefix)
        
        # 发送工作流到ComfyUI
        response = self.queue_prompt(workflow)
        prompt_id = response['prompt_id']
        
        print(f"已提交任务，ID: {prompt_id}")
        
        # 等待处理完成
        while True:
            history = self.get_history(prompt_id)
            if prompt_id in history and history[prompt_id].get("status", {}).get("completed", False):
                print(f"任务 {prompt_id} 完成")
                break
            time.sleep(1)
        
        return prompt_id

def batch_process_videos(video_paths, output_folder="output"):
    """批量处理视频"""
    client = ComfyUIClient()
    
    for i, video_path in enumerate(video_paths):
        print(f"正在处理第 {i+1}/{len(video_paths)} 个视频: {video_path}")
        
        output_prefix = f"{output_folder}/processed_{i+1}"
        client.process_video(video_path, output_prefix)
        
        print(f"已完成处理: {video_path}")

def batch_process_folder(folder_path, output_folder="output", supported_formats=('.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm')):
    """批量处理文件夹中的视频文件"""
    # 获取文件夹中所有视频文件
    video_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(supported_formats):
                video_files.append(os.path.join(root, file))
    
    print(f"找到 {len(video_files)} 个视频文件")
    
    # 批量处理视频
    batch_process_videos(video_files, output_folder)

# 使用示例
if __name__ == "__main__":
    # 单个视频处理示例

    # 创建tkinter根窗口并隐藏它
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 让用户选择包含视频的文件夹
    INPUT_FOLDER = filedialog.askdirectory(title="选择包含视频的文件夹")
    
    # 如果用户取消了选择，则退出程序
    if not INPUT_FOLDER:
        print("未选择文件夹，程序退出")
    else:
        print(f"选择的文件夹: {INPUT_FOLDER}")
        # 批量处理文件夹示例
        #folder_path = r"J:\AI-T8-video-onekey-20251005\ComfyUI\output\美女短视频\守岸人"  # 替换为包含视频的文件夹路径
        batch_process_folder(INPUT_FOLDER, "output_folder_name")
    