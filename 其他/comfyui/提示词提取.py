import os
import json
from PIL import Image
import shutil
import ffmpeg
import tkinter as tk
from tkinter import filedialog
import sys

def extract_comfyui_prompts_from_image(png_path):
    """
    从单个图像文件中提取ComfyUI提示词
    """
    try:
        with Image.open(png_path) as img:
            if img.format != "PNG":
                return ""

            # 读取 ComfyUI 埋入的 prompt JSON 数据
            prompt_json = img.info.get("prompt")
            if not prompt_json:
                return ""

            data = json.loads(prompt_json)
            
            # 直接查找节点113的文本
            if "113" in data and data["113"].get("class_type") == "CLIPTextEncode":
                positive_prompt = data["113"]["inputs"].get("text", "").strip()
                return positive_prompt
            
            return ""

    except Exception as e:
        print(f"处理 {png_path} 出错：{str(e)}")
        return ""

def extract_comfyui_prompts_from_video(video_path):
    """
    从视频文件中提取ComfyUI提示词
    """
    try:
        print(f"正在分析视频文件: {video_path}")
        
        # 使用ffmpeg读取视频元数据
        probe = ffmpeg.probe(video_path)

        format_metadata = probe.get('format', {}).get('tags', {})
        if format_metadata:
            if 'comment' in format_metadata:
                comment = json.loads(format_metadata['comment']).get('workflow', {}).get('nodes', {})

                prompt_nodes = None
                for x in comment:
                    if x.get('id', {}) == 113:
                        prompt_nodes = x
                        positive_prompt = prompt_nodes.get('widgets_values', {})[0]
                        return positive_prompt

        print("\n未能找到ComfyUI提示词信息")
        return ""

    except Exception as e:
        print(f"处理 {video_path} 出错：{str(e)}")
        return ""

def extract_comfyui_prompts(file_path):
    """
    统一接口：根据文件类型自动选择提取方法
    """
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return ""
    
    _, ext = os.path.splitext(file_path.lower())
    
    if ext in ['.png', '.jpg', '.jpeg']:
        return extract_comfyui_prompts_from_image(file_path)
    elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
        return extract_comfyui_prompts_from_video(file_path)
    else:
        print(f"不支持的文件格式: {ext}")
        return ""

def get_user_choice():
    """获取用户的选择：仅图片、仅视频或全部"""
    print("请选择要提取的文件类型:")
    print("1. 仅图片文件")
    print("2. 仅视频文件") 
    print("3. 全部文件")
    
    while True:
        choice = input("请输入选项 (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            return int(choice)
        else:
            print("无效输入，请输入 1、2 或 3")

def select_folder(title):
    """打开文件夹选择对话框"""
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 设置窗口置顶
    root.attributes('-topmost', True)
    
    # 打开文件夹选择对话框
    folder_path = filedialog.askdirectory(title=title)
    
    # 重置置顶属性
    root.attributes('-topmost', False)
    
    root.destroy()
    return folder_path

def process_files(input_folder, output_folder, file_types):
    """处理文件并提取提示词"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    processed_count = 0
    
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file.lower())
            
            # 根据用户选择过滤文件类型
            should_process = False
            if file_types == 1 and ext in ['.png', '.jpg', '.jpeg']:  # 仅图片
                should_process = True
            elif file_types == 2 and ext in ['.mp4', '.avi', '.mov', '.mkv']:  # 仅视频
                should_process = True
            elif file_types == 3 and ext in ['.png', '.jpg', '.jpeg', '.mp4', '.avi', '.mov', '.mkv']:  # 全部
                should_process = True
            
            if should_process:
                print(f"正在处理: {file_path}")
                prompt = extract_comfyui_prompts(file_path)
                
                if prompt:
                    # 生成同名txt文件
                    file_name_without_ext = os.path.splitext(file)[0]
                    txt_file_path = os.path.join(output_folder, f"{file_name_without_ext}.txt")
                    
                    # 写入提示词到txt文件
                    with open(txt_file_path, 'w', encoding='utf-8') as f:
                        f.write(prompt)
                    print(f"提取到提示词并保存到: {txt_file_path}")
                    processed_count += 1
                    
                    # 复制原文件到输出文件夹
                    destination_path = os.path.join(output_folder, file)
                    try:
                        shutil.copy2(file_path, destination_path)
                        print(f"已复制文件到: {destination_path}")
                    except Exception as e:
                        print(f"复制文件失败: {str(e)}")
                else:
                    print(f"未找到提示词，跳过文件: {file_path}")
    
    print(f"\n处理完成！共处理了 {processed_count} 个文件")
    print(f"文件已保存到: {output_folder}")

def main():
    """主函数"""
    print("ComfyUI 提示词提取工具")
    print("=" * 30)
    
    # 获取用户选择
    choice = get_user_choice()
    
    # 选择输入文件夹
    print("\n请选择输入文件夹...")
    input_folder = select_folder("选择包含媒体文件的文件夹")
    if not input_folder:
        print("未选择输入文件夹，程序退出")
        return
    
    # 选择输出文件夹
    print("\n请选择输出文件夹...")
    output_folder = select_folder("选择保存结果的文件夹")
    if not output_folder:
        print("未选择输出文件夹，程序退出")
        return
    
    # 处理文件
    print(f"\n开始处理...")
    print(f"输入文件夹: {input_folder}")
    print(f"输出文件夹: {output_folder}")
    print(f"处理类型: {'仅图片' if choice == 1 else '仅视频' if choice == 2 else '全部文件'}")
    
    process_files(input_folder, output_folder, choice)

if __name__ == "__main__":
    main()