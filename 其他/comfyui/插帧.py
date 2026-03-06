import json
import requests
import time
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

class ComfyUIBatchProcessor:
    def __init__(self, server_address="127.0.0.1:8188"):
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

    def update_output_settings(self, workflow_json, output_prefix, output_path=None):
        """更新输出设置"""
        for node_id, node in workflow_json.items():
            if node['class_type'] == 'VHS_VideoCombine':
                # 设置文件名前缀
                node['inputs']['filename_prefix'] = output_prefix
                
                # 处理输出路径 - 通过相对路径方式
                if output_path:
                    # 将输出路径转换为相对于ComfyUI输出目录的路径
                    # 这样可以在文件名前缀中包含路径信息
                    path_parts = Path(output_prefix).parts
                    if len(path_parts) > 1:
                        # 如果有子目录结构，在前缀中体现
                        node['inputs']['filename_prefix'] = str(Path(*path_parts))
                    print(f"输出文件名前缀: {node['inputs']['filename_prefix']}")
                    print(f"注意: 实际输出路径由ComfyUI服务器配置决定")
                    print(f"建议在ComfyUI中检查输出目录设置")
                else:
                    print(f"已设置输出前缀: {output_prefix}")
                break

    def process_video(self, input_video_path, output_prefix, workflow_path, output_path=None):
        """处理单个视频"""
        # 加载并修改工作流
        workflow = self.load_workflow(workflow_path)
        self.update_video_input(workflow, input_video_path)
        self.update_output_settings(workflow, output_prefix, output_path)

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
        output_files = []
        max_wait_time = 300  # 最大等待5分钟
        start_time = time.time()
        
        while status is None or status.get('status_str') != 'success':
            try:
                history = self.get_history(prompt_id)
                if prompt_id in history:
                    prompt_data = history[prompt_id]
                    if 'status' in prompt_data and prompt_data['status']['completed']:
                        status = prompt_data['status']
                        # 获取输出文件信息
                        if 'outputs' in prompt_data:
                            for node_id, node_outputs in prompt_data['outputs'].items():
                                if 'videos' in node_outputs:
                                    for video_info in node_outputs['videos']:
                                        if 'filename' in video_info:
                                            output_files.append(video_info['filename'])
                        break
                    elif time.time() - start_time > max_wait_time:
                        print(f"任务超时 ({max_wait_time}秒)")
                        return False
            except Exception as e:
                print(f"获取任务状态失败: {str(e)}")
                if time.time() - start_time > max_wait_time:
                    return False
                time.sleep(2)
                continue
            time.sleep(2)  # 等待2秒后检查

        if output_files:
            print(f"视频处理完成: {input_video_path}")
            print(f"生成的文件: {output_files}")
            if output_path:
                print(f"建议手动将文件移动到: {output_path}")
        else:
            print(f"视频处理完成，但未找到输出文件信息: {input_video_path}")
        
        return True

    def get_all_video_files(self, input_path, extensions=('.mp4', '.mov', '.avi', '.mkv')):
        """递归获取所有视频文件，包括子文件夹中的文件"""
        video_files = []
        input_path = Path(input_path)
        
        # 递归遍历所有子目录
        for ext in extensions:
            video_files.extend(input_path.rglob(f"*{ext}"))
        
        # 去除可能的重复项
        video_files = list(set(video_files))
        return video_files

    def batch_process(self, input_folder, workflow_path, output_folder=None, extensions=('.mp4', '.mov', '.avi', '.mkv')):
        """批量处理视频"""
        input_path = Path(input_folder)

        # 获取所有视频文件（包括子文件夹）
        video_files = self.get_all_video_files(input_path, extensions)

        if not video_files:
            print(f"在 {input_folder} 及其子文件夹中没有找到视频文件")
            return

        print(f"找到 {len(video_files)} 个视频文件")
        
        # 创建输出目录映射
        output_mapping = {}

        # 处理每个视频
        for i, video_file in enumerate(video_files):
            print(f"\n处理第 {i+1}/{len(video_files)} 个视频: {video_file}")
            
            # 生成相对于输入文件夹的路径结构
            relative_path = video_file.relative_to(input_path)
            # 修改: 使用时间戳作为文件名后缀
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = f"{relative_path.parent / relative_path.stem}_interpolated_{timestamp}"
            
            # 构造输出前缀和实际输出路径
            output_prefix = str(base_name)
            actual_output_path = None
            
            if output_folder:
                # 创建对应的输出子目录结构
                output_subdir = Path(output_folder) / relative_path.parent
                output_subdir.mkdir(parents=True, exist_ok=True)
                actual_output_path = str(output_subdir)
                output_mapping[base_name] = str(output_subdir)
                print(f"输出目录: {actual_output_path}")
            
            try:
                result = self.process_video(
                    input_video_path=str(video_file),
                    output_prefix=output_prefix,
                    workflow_path=workflow_path,
                    output_path=actual_output_path
                )
                
                if result:
                    print(f"✓ 视频 {video_file.name} 处理成功")
                    if output_folder:
                        print(f"  建议输出位置: {actual_output_path}")
                else:
                    print(f"✗ 视频 {video_file.name} 处理失败")
                    
            except Exception as e:
                print(f"处理视频 {video_file.name} 时出错: {str(e)}")
                continue
        
        # 显示输出路径说明
        if output_folder:
            print(f"\n=== 输出路径说明 ===")
            print(f"指定的输出文件夹: {output_folder}")
            print(f"注意: ComfyUI会将文件保存在其配置的输出目录中")
            print(f"您需要手动将生成的文件从ComfyUI输出目录移动到指定的输出文件夹")
            print(f"或者在ComfyUI中修改默认输出目录设置")

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
    
    # 让用户选择输出文件夹（可选）
    OUTPUT_FOLDER = filedialog.askdirectory(title="选择输出文件夹（可选，取消则使用默认输出位置）")
    if not OUTPUT_FOLDER:
        OUTPUT_FOLDER = None
        print("未选择输出文件夹，将使用ComfyUI默认输出位置")
    else:
        print(f"输出文件夹: {OUTPUT_FOLDER}")
    
    WORKFLOW_PATH = r"其他\comfyui\视频插帧.json"
    
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
    processor = ComfyUIBatchProcessor(server_address="127.0.0.1:8188")  # 修改为您的ComfyUI服务器地址
    
    # 批量处理视频
    processor.batch_process(INPUT_FOLDER, WORKFLOW_PATH, OUTPUT_FOLDER)

if __name__ == "__main__":
    main()