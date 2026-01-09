import os
import subprocess
import sys
from pathlib import Path

def change_video_fps(input_folder, target_fps=30):
    """
    批量修改指定文件夹中所有视频的帧率
    
    Args:
        input_folder (str): 包含视频文件的文件夹路径
        target_fps (int): 目标帧率，默认为30fps
    """
    
    # 支持的视频格式
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']
    
    # 获取文件夹中的所有视频文件
    video_files = []
    for ext in video_extensions:
        video_files.extend(Path(input_folder).glob(f'*{ext}'))
        video_files.extend(Path(input_folder).glob(f'*{ext.upper()}'))
    
    if not video_files:
        print(f"在 {input_folder} 中未找到视频文件")
        return
    
    print(f"找到 {len(video_files)} 个视频文件")
    
    # 处理每个视频文件
    for video_path in video_files:
        print(f"正在处理: {video_path.name}")
        
        # 创建临时文件路径
        temp_path = video_path.parent / f"temp_{video_path.name}"
        
        try:
            # 使用ffmpeg修改帧率
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vf', f'fps={target_fps}',
                '-c:a', 'copy',  # 复制音频流而不重新编码
                str(temp_path)
            ]
            
            # 执行命令，避免文本解码问题
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                # 删除原文件
                os.remove(video_path)
                # 重命名临时文件为原文件名
                os.rename(temp_path, video_path)
                print(f"成功修改 {video_path.name} 的帧率为 {target_fps}fps")
            else:
                # 如果失败，删除临时文件
                if temp_path.exists():
                    os.remove(temp_path)
                print(f"处理 {video_path.name} 失败: {result.stderr}")
                
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                os.remove(temp_path)
            print(f"处理 {video_path.name} 时发生错误: {str(e)}")

def main():
    # 获取用户输入的文件夹路径
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = input("请输入包含视频文件的文件夹路径: ").strip()
    
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"错误: 文件夹 '{folder_path}' 不存在")
        return
    
    if not os.path.isdir(folder_path):
        print(f"错误: '{folder_path}' 不是一个有效的文件夹")
        return
    
    # 获取目标帧率
    try:
        target_fps = input("请输入目标帧率 (默认30): ").strip()
        if target_fps == "":
            target_fps = 30
        else:
            target_fps = int(target_fps)
    except ValueError:
        print("错误: 帧率必须是一个数字")
        return
    
    # 确认操作
    print(f"\n将对文件夹 '{folder_path}' 中的所有视频进行帧率转换")
    print(f"目标帧率: {target_fps}fps")
    confirm = input("确认继续吗? (y/N): ").strip().lower()
    
    if confirm not in ['y', 'yes']:
        print("操作已取消")
        return
    
    # 执行帧率转换
    change_video_fps(folder_path, target_fps)

if __name__ == "__main__":
    main()