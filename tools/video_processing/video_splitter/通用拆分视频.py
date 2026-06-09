import os
import cv2
from math import ceil
import subprocess

def split_video_by_seconds(video_path, interval_seconds):
    """
    按指定秒数分割视频
    
    Args:
        video_path (str): 视频文件路径
        interval_seconds (int): 分割间隔秒数
    """
    # 检查视频文件是否存在
    if not os.path.exists(video_path):
        print(f"错误: 视频文件 {video_path} 不存在")
        return
    
    # 获取视频所在目录和文件名
    video_dir = os.path.dirname(video_path)
    video_name = os.path.basename(video_path)
    video_name_without_ext = os.path.splitext(video_name)[0]
    
    # 创建保存分割视频的文件夹
    output_folder = os.path.join(video_dir, f"{video_name_without_ext}_segments")
    os.makedirs(output_folder, exist_ok=True)
    
    # 打开视频文件
    cap = cv2.VideoCapture(video_path)
    
    # 获取视频属性
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    # 计算每个片段的帧数
    frames_per_segment = int(interval_seconds * fps)
    total_segments = ceil(total_frames / frames_per_segment)
    
    print(f"视频总时长: {duration:.2f} 秒")
    print(f"FPS: {fps}")
    print(f"总共将分割为 {total_segments} 个片段")
    
    cap.release()
    
    # 使用ffmpeg分割视频以保留音频
    for segment_index in range(total_segments):
        start_time = segment_index * interval_seconds
        end_time = min((segment_index + 1) * interval_seconds, duration)
        
        # 构造输出文件路径
        output_path = os.path.join(output_folder, f"{video_name_without_ext}_part_{segment_index+1:03d}.mp4")
        
        # 使用ffmpeg命令分割视频并保留音频
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(start_time),
            '-t', str(end_time - start_time),
            '-c', 'copy',  # 直接复制编解码，速度更快
            output_path,
            '-y'  # 覆盖已存在的文件
        ]
        
        # 执行ffmpeg命令
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"已保存片段: {os.path.basename(output_path)}")
        except subprocess.CalledProcessError as e:
            print(f"分割片段 {segment_index+1} 时出错: {e}")
        except FileNotFoundError:
            print("错误: 未找到ffmpeg命令，请确保已安装ffmpeg并添加到系统PATH中")
            return
            
        # 显示进度
        progress = (segment_index + 1) / total_segments * 100
        print(f"\r处理进度: {progress:.1f}%", end="", flush=True)
    
    print(f"\n所有片段已保存至: {output_folder}")

if __name__ == "__main__":
    # 获取用户输入
    video_path = input("请输入视频文件路径: ").strip()
    interval_seconds = int(input("请输入分割间隔秒数: "))
    
    # 执行分割
    split_video_by_seconds(video_path, interval_seconds)