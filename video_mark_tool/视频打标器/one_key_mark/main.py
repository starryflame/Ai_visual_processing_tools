import os
import sys
import tkinter as tk
from tkinter import filedialog
from video_processor import VideoProcessor
from image_processor import ImageProcessor
from config_manager import ConfigManager

def main():
    """主程序入口"""
    # 创建隐藏的根窗口
    root = tk.Tk()
    root.withdraw()
    
    print("批量视频处理工具")
    print("=" * 30)
    
    # 检查是否通过命令行参数提供了输入文件夹路径
    if len(sys.argv) > 1:
        input_folder = sys.argv[1]
        if not os.path.exists(input_folder):
            print(f"指定的文件夹不存在: {input_folder}")
            return
        print(f"使用命令行参数指定的文件夹: {input_folder}")
    else:
        input_folder = filedialog.askdirectory(title="选择包含视频文件的文件夹")
        if not input_folder:
            print("未选择文件夹，程序退出")
            return
        print(f"选择的文件夹: {input_folder}")
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 初始化处理器
    video_processor = VideoProcessor(config_manager)
    image_processor = ImageProcessor(config_manager)
    
    # 检测文件夹中的内容类型并相应处理
    video_files, image_files = video_processor.detect_file_types(input_folder)
    
    if video_files and image_files:
        print(f"检测到 {len(video_files)} 个视频文件和 {len(image_files)} 个图片文件")
        # 处理视频文件
        print("开始处理视频文件...")
        split_dir, split_files = video_processor.process_folder_for_splitting(input_folder)
        
        # 如果有分割后的文件，则处理这些文件；否则处理原始文件
        if split_files:
            files_to_process = split_files
        else:
            files_to_process = video_files
            
        for i, video_file in enumerate(files_to_process, 1):
            try:
                print(f"[{i}/{len(files_to_process)}] 正在处理: {os.path.basename(video_file)}")
                video_processor.process_video(video_file)
                print(f"[{i}/{len(files_to_process)}] 完成处理: {os.path.basename(video_file)}")
            except Exception as e:
                print(f"处理视频 {video_file} 时出错: {e}")
        
        # 处理图片文件
        print("开始处理图片文件...")
        common_output_dir = os.path.join(input_folder, "processed_images")
        os.makedirs(common_output_dir, exist_ok=True)
        
        for i, image_file in enumerate(image_files, 1):
            try:
                print(f"[{i}/{len(image_files)}] 正在处理: {os.path.basename(image_file)}")
                image_processor.process_image(image_file, common_output_dir)
                print(f"[{i}/{len(image_files)}] 完成处理: {os.path.basename(image_file)}")
            except Exception as e:
                print(f"处理图片 {image_file} 时出错: {e}")
                
    elif video_files:
        print(f"检测到 {len(video_files)} 个视频文件")
        video_processor.process_all_videos(input_folder)
    elif image_files:
        print(f"检测到 {len(image_files)} 个图片文件")
        image_processor.process_all_images(input_folder)
    else:
        print("未找到支持的视频或图片文件")
        
    print("所有文件处理完成!")

if __name__ == "__main__":
    main()