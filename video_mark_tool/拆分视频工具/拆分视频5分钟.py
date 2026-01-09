import os
import subprocess
import math
from pathlib import Path
import shutil

def get_video_duration(video_path):
    """获取视频时长"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"无法获取视频时长: {e}")
        return 0

def get_video_framerate(video_path):
    """获取视频帧率"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1', video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        framerate_str = result.stdout.strip()
        if '/' in framerate_str:
            num, den = map(int, framerate_str.split('/'))
            return num / den
        else:
            return float(framerate_str)
    except Exception as e:
        print(f"无法获取视频帧率: {e}")
        return 0


# 添加进度条显示函数
def show_progress(current, total, prefix='', suffix='', length=30):
    """
    显示进度条
    :param current: 当前进度
    :param total: 总量
    :param prefix: 前缀文字
    :param suffix: 后缀文字
    :param length: 进度条长度
    """
    if total == 0:
        return
    percent = int(100 * (current / float(total)))
    filled_length = int(length * current // total)
    bar = '█' * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if current == total:
        print()

def split_video_intelligently(input_path, output_dir, filename):
    """智能分割视频，尽量对半分且避免过小片段"""
    duration = get_video_duration(input_path)
    if duration <= 300:  # 5分钟=300秒
        print(f"{filename} 时长不足5分钟，无需分割")
        return
    
    # 计算分割策略：尽量对半分，但确保每段不超过5分钟
    num_segments = max(2, math.ceil(duration / 300))  # 至少分成2段，每段不超过5分钟
    segment_duration = duration / num_segments
    
    # 如果分割后每段都小于30秒，则不进行分割
    if segment_duration < 30:
        print(f"{filename} 分割后片段太小，跳过分割")
        return
    
    print(f"将 {filename} 分割为 {num_segments} 个片段，每段约{segment_duration/60:.1f}分钟")
    
    # 创建输出目录
    base_name = Path(filename).stem
    suffix = Path(filename).suffix
    
    # 分割前n-1个片段
    for i in range(num_segments - 1):
        start_time = i * segment_duration
        end_time = (i + 1) * segment_duration
        
        output_file = os.path.join(output_dir, f"{base_name}_part{i+1:02d}{suffix}")
        cmd = [
            'ffmpeg', '-i', input_path,
            '-ss', str(start_time), '-to', str(end_time),
            '-c', 'copy', output_file
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"已生成: {os.path.basename(output_file)} ({end_time-start_time:.1f}秒)")
    
    # 处理最后一个片段
    start_time = (num_segments - 1) * segment_duration
    output_file = os.path.join(output_dir, f"{base_name}_part{num_segments:02d}{suffix}")
    cmd = [
        'ffmpeg', '-i', input_path,
        '-ss', str(start_time),
        '-c', 'copy', output_file
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"已生成: {os.path.basename(output_file)} ({duration-start_time:.1f}秒)")


def split_video_to_clips(input_path, output_dir, target_duration=5, target_fps=16, txt_content=""):
    """将视频切分为指定时长的片段，并调整帧率"""
    duration = get_video_duration(input_path)
    filename = os.path.basename(input_path)
    
    # 计算片段数量
    num_clips = math.ceil(duration / target_duration)
    
    print(f"将 {filename} 切分为 {num_clips} 个 {target_duration} 秒的片段")
    
    # 创建输出目录
    base_name = Path(filename).stem
    suffix = Path(filename).suffix
    
    video_codec = 'libx264'
    preset = 'fast'
    quality = '23'
    
    # 切分视频片段并调整帧率
    for i in range(num_clips):
        start_time = i * target_duration
        # 确保最后一段不会超出视频时长
        clip_duration = min(target_duration, duration - start_time)
        
        if clip_duration <= 0:
            break
            
        output_file = os.path.join(output_dir, f"{base_name}_clip{i+1:03d}{suffix}")
        
        # 构建命令行参数
        cmd = [
            'ffmpeg', '-i', input_path,
            '-ss', str(start_time),
            '-t', str(clip_duration),
            '-r', str(target_fps),  # 设置帧率
            '-c:v', video_codec,    # 视频编码器
        ]
        
        # 根据编码器类型添加特定参数
        cmd.extend(['-preset', preset, '-crf', quality])
            
        cmd.extend([
            '-c:a', 'aac',          # 音频编码
            '-ar', '44100',         # 音频采样率
            '-b:a', '128k',         # 音频比特率
            output_file
        ])
        
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"处理片段时出错: {result.stderr.decode()}")
        else:
            print(f"已生成: {os.path.basename(output_file)} ({clip_duration:.1f}秒, {target_fps}fps)")
            
            # 为每个视频片段生成同名txt文件
            if txt_content:
                txt_file = os.path.join(output_dir, f"{base_name}_clip{i+1:03d}.txt")
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(txt_content)
                print(f"已生成: {os.path.basename(txt_file)}")


def process_folder(input_folder, target_duration=5, target_fps=16, txt_content=""):
    """处理指定文件夹中的所有视频文件"""
    # 支持的视频格式
    video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp'}
    
    
    # 创建输出目录
    output_dir = os.path.join(input_folder, "split_videos")
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有视频文件列表
    video_files = [f for f in os.listdir(input_folder) 
                  if os.path.isfile(os.path.join(input_folder, f)) 
                  and Path(f).suffix.lower() in video_extensions]
    
    # 显示总体进度
    total_files = len(video_files)
    print(f"共找到 {total_files} 个视频文件需要处理")
    
    # 遍历文件夹中的所有文件
    for idx, filename in enumerate(video_files, 1):
        file_path = os.path.join(input_folder, filename)
        
        # 显示文件处理进度
        print(f"\n[{idx}/{total_files}] 正在处理: {filename}")
        
        # 检查是否为文件且为视频格式
        if os.path.isfile(file_path) and Path(filename).suffix.lower() in video_extensions:
            duration = get_video_duration(file_path)
            
            # 如果视频小于等于目标时长，直接复制并调整帧率到输出目录
            if duration <= target_duration:
                output_file = os.path.join(output_dir, filename)
                # 即使时长符合要求，也需要调整帧率
                
                video_codec = 'libx264'
                preset = 'fast'
                quality = '23'
                
                cmd = [
                    'ffmpeg', '-i', file_path,
                    '-r', str(target_fps),      # 设置帧率
                    '-c:v', video_codec,        # 视频编码器
                ]
                
                # 根据编码器类型添加特定参数
                cmd.extend(['-preset', preset, '-crf', quality])
                    
                cmd.extend([
                    '-c:a', 'aac',              # 音频编码
                    '-ar', '44100',             # 音频采样率
                    '-b:a', '128k',             # 音频比特率
                    output_file
                ])
                
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                if result.returncode != 0:
                    print(f"处理文件时出错: {result.stderr.decode()}")
                else:
                    print(f"已处理: {filename} ({target_fps}fps)")
                    
                    # 为视频文件生成同名txt文件
                    if txt_content:
                        base_name = Path(filename).stem
                        txt_file = os.path.join(output_dir, f"{base_name}.txt")
                        with open(txt_file, 'w', encoding='utf-8') as f:
                            f.write(txt_content)
                        print(f"已生成: {base_name}.txt")
            else:
                # 否则进行分割
                split_video_to_clips(file_path, output_dir, target_duration, target_fps, txt_content)
        
        # 在这里显示总进度
        show_progress(idx, total_files, prefix='总进度:', suffix='完成')
    
    print(f"所有视频处理完成，分割文件保存在: {output_dir}")

if __name__ == "__main__":
    # 获取用户输入的文件夹路径
    folder_path = input("请输入要处理的文件夹路径: ").strip()
    
    # 获取用户输入的txt文件内容
    txt_content = input("请输入要写入txt文件的内容: ").strip()
    
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print("指定的文件夹不存在!")
    elif not os.path.isdir(folder_path):
        print("指定路径不是一个文件夹!")
    else:
        process_folder(folder_path, target_duration=5, target_fps=16, txt_content=txt_content)