import cv2
import os
from pathlib import Path

def extract_first_frame(video_folder, output_folder=r"E:\Downloads\sese\sese5s\frames"):
    """
    提取文件夹中所有视频的首帧
    
    Args:
        video_folder (str): 包含视频文件的文件夹路径
        output_folder (str): 输出图片的文件夹路径，默认为视频文件夹下的'frames'子文件夹
    """
    # 检查输入文件夹是否存在
    if not os.path.exists(video_folder):
        print(f"错误: 输入文件夹 '{video_folder}' 不存在")
        return
    
    # 如果没有指定输出文件夹，则在视频文件夹下创建frames子文件夹
    if output_folder is None:
        output_folder = os.path.join(video_folder, 'frames')
    
    # 创建输出文件夹
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    print(f"输出文件夹: {output_folder}")
    
    # 检查输出文件夹是否可写
    if not os.access(output_folder, os.W_OK):
        print(f"错误: 输出文件夹 '{output_folder}' 不可写")
        return
    
    # 支持的视频格式
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    
    # 获取所有文件
    files = os.listdir(video_folder)
    print(f"找到 {len(files)} 个文件")
    
    processed_count = 0
    
    # 遍历文件夹中的所有文件
    for filename in files:
        file_path = os.path.join(video_folder, filename)
        
        # 检查是否为文件且扩展名符合视频格式
        if os.path.isfile(file_path) and Path(filename).suffix.lower() in video_extensions:
            print(f"正在处理: {filename}")
            
            # 打开视频文件
            cap = cv2.VideoCapture(file_path)
            
            # 检查视频是否成功打开
            if not cap.isOpened():
                print(f"错误: 无法打开视频文件: {filename}")
                continue
            
            # 读取第一帧
            ret, frame = cap.read()
            
            if ret:
                # 生成输出文件名
                output_filename = f"{Path(filename).stem}.jpg"
                output_path = os.path.join(output_folder, output_filename)
                
                # 尝试多种方式保存图片
                success = False
                
                # 方法1: 直接保存
                try:
                    success = cv2.imwrite(output_path, frame)
                except Exception as e:
                    print(f"直接保存失败: {e}")
                
                # 方法2: 指定JPEG质量参数
                if not success:
                    try:
                        success = cv2.imwrite(output_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                    except Exception as e:
                        print(f"指定质量参数保存失败: {e}")
                
                # 方法3: 保存为PNG格式
                if not success:
                    png_output_path = os.path.join(output_folder, f"{Path(filename).stem}.png")
                    try:
                        success = cv2.imwrite(png_output_path, frame)
                        if success:
                            print(f"已另存为PNG格式: {Path(filename).stem}.png")
                    except Exception as e:
                        print(f"保存为PNG也失败: {e}")
                
                if success:
                    print(f"已保存: {output_filename}")
                    processed_count += 1
                else:
                    print(f"错误: 无法保存图片: {output_filename}，请检查磁盘空间和文件权限")
            else:
                print(f"错误: 无法读取视频的第一帧: {filename}")
            
            # 释放视频捕获对象
            cap.release()
        else:
            # 显示被跳过的文件
            if os.path.isfile(file_path):
                print(f"跳过非视频文件: {filename}")
    
    print(f"\n处理完成! 共处理了 {processed_count} 个视频文件")
    print(f"请检查 '{output_folder}' 文件夹")

if __name__ == "__main__":
    # 设置视频文件夹路径
    video_folder = r"E:\Downloads\sese\sese5s"
    
    # 检查文件夹是否存在
    if not os.path.exists(video_folder):
        print("指定的文件夹不存在!")
        input("按回车键退出...")
    else:
        # 显示找到的视频文件数量
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
        video_files = [f for f in os.listdir(video_folder) 
                      if os.path.isfile(os.path.join(video_folder, f)) 
                      and Path(f).suffix.lower() in video_extensions]
        print(f"在文件夹中找到 {len(video_files)} 个视频文件")
        
        # 提取首帧
        extract_first_frame(video_folder)
        print("首帧提取完成!")
        input("按回车键退出...")