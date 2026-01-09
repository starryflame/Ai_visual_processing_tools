import os
import cv2
import json
import numpy as np
import subprocess
import math
import shutil
from pathlib import Path
from ai_processor import AIProcessor
import logging

logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, config_manager):
        self.config = config_manager
        self.ai_processor = AIProcessor(config_manager)
        # 支持的视频格式
        self.supported_formats = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
    
    def get_video_files(self, folder):
        """获取文件夹中所有视频文件"""
        video_files = []
        for file in os.listdir(folder):
            if file.lower().endswith(self.supported_formats):
                video_files.append(os.path.join(folder, file))
        return video_files

    def resize_to_720p(self, frame):
        """将帧调整为720p分辨率"""
        target_height = self.config.getint('PROCESSING', 'target_frame_height', fallback=720)
        h, w = frame.shape[:2]
        
        if h <= target_height:
            return frame
            
        new_height = target_height
        new_width = int(w * (new_height / h))
        resized_frame = cv2.resize(frame, (new_width, new_height))
        return resized_frame

    def process_video(self, video_path):
        """处理单个视频文件"""
        logger.info(f"开始处理视频: {video_path}")
        print(f"开始处理视频: {os.path.basename(video_path)}")
        
        # 创建输出文件夹
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.join(os.path.dirname(video_path), f"{video_name}")
        os.makedirs(output_dir, exist_ok=True)
        
        # 打开视频
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"无法打开视频文件: {video_path}")
            return
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        if total_frames <= 0 or fps <= 0:
            logger.error(f"无效的视频信息: {video_path}")
            cap.release()
            return
            
        logger.info(f"视频信息 - 总帧数: {total_frames}, FPS: {fps}")
        print(f"视频信息 - 总帧数: {total_frames}, FPS: {fps}")
        
        # 从配置读取目标帧率
        target_fps = self.config.getint('PROCESSING', 'target_frame_rate', fallback=24)
        if fps > target_fps:
            frame_interval = fps / target_fps
            effective_fps = target_fps
        else:
            frame_interval = 1
            effective_fps = fps
            
        # 处理所有帧
        processed_frames = []
        i = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if i % frame_interval < 1:
                # 转换颜色格式
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 调整为720p
                frame = self.resize_to_720p(frame)
                processed_frames.append(frame)
                
            i += 1
            
        cap.release()
        
        # 计算分段参数
        segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
        frames_per_segment = int(segment_duration * effective_fps)
        
        # 分段处理
        segments = []
        current_frame = 0
        segment_index = 0
        
        total_segments = math.ceil(len(processed_frames) / frames_per_segment)
        print(f"视频将被分割为 {total_segments} 个片段")
        
        # 加载现有元数据（如果存在）
        metadata_path = os.path.join(output_dir, "metadata.json")
        existing_metadata = {}
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    existing_metadata = json.load(f)
            except Exception as e:
                logger.warning(f"读取现有元数据失败: {e}")
        
        while current_frame < len(processed_frames):
            segment_end = min(current_frame + frames_per_segment - 1, len(processed_frames) - 1)
            
            # 提取片段帧
            segment_frames = processed_frames[current_frame:segment_end+1]
            
            # 抽帧以提高性能
            max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
            if len(segment_frames) > max_sample_frames:
                indices = np.linspace(0, len(segment_frames)-1, max_sample_frames, dtype=int)
                sampled_frames = [segment_frames[i] for i in indices]
            else:
                sampled_frames = segment_frames
                
            # 如果只有一帧，复制以满足视频处理要求
            if len(sampled_frames) == 1:
                sampled_frames.append(sampled_frames[0])
            
            # 生成安全的文件名前缀
            filename_prefix = f"{segment_index+1:03d}"
            video_output_path = os.path.join(output_dir, f"{filename_prefix}*.mp4")
            txt_output_path = os.path.join(output_dir, f"{filename_prefix}*.txt")
            
            # 检查是否已有对应的标签文件
            existing_txt_files = [f for f in os.listdir(output_dir) if f.startswith(filename_prefix) and f.endswith('.txt')]
            existing_video_files = [f for f in os.listdir(output_dir) if f.startswith(filename_prefix) and f.endswith('.mp4')]
            
            caption = None
            if existing_txt_files:
                # 如果已存在标签文件，读取现有标签
                txt_file = existing_txt_files[0]
                txt_output_path = os.path.join(output_dir, txt_file)
                try:
                    with open(txt_output_path, 'r', encoding='utf-8') as f:
                        caption = f.read().strip()
                    print(f"  片段 {segment_index+1} 已存在标签，跳过AI生成: {txt_file}")
                except Exception as e:
                    print(f"  读取现有标签失败: {e}，重新生成")
            
            # 如果没有标签或者读取失败，则生成新标签
            if caption is None:
                print(f"  正在为片段 {segment_index+1}/{total_segments} 生成描述...")
                caption = self.ai_processor.generate_video_caption_with_ai(sampled_frames)
                print(f"  片段 {segment_index+1} 描述: {caption[:100]}...")
            
            # 保存片段视频（即使已存在也要检查完整性）
            if segment_frames:
                first_frame = segment_frames[0]
                height, width = first_frame.shape[:2]
                
                # 生成安全的文件名
                safe_caption = "".join(c for c in caption if c.isalnum() or c in (' ', '-', '_')).rstrip()
                max_filename_length = self.config.getint('PROCESSING', 'max_filename_length', fallback=50)
                safe_caption = safe_caption[:max_filename_length] if len(safe_caption) > max_filename_length else safe_caption
                safe_caption = safe_caption.replace(" ", "_") if safe_caption else f"segment_{segment_index+1:03d}"
                
                # 生成文件名
                filename = f"{segment_index+1:03d}_{safe_caption}"
                video_output_path = os.path.join(output_dir, f"{filename}.mp4")
                txt_output_path = os.path.join(output_dir, f"{filename}.txt")
                
                # 只有当视频文件不存在时才创建视频
                if not os.path.exists(video_output_path) or not existing_video_files:
                    # 写入视频
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    out = cv2.VideoWriter(video_output_path, fourcc, effective_fps, (width, height))
                    
                    for frame in segment_frames:
                        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        out.write(frame_bgr)
                    out.release()
                    print(f"  已创建视频片段: {filename}.mp4")
                else:
                    print(f"  视频片段已存在，跳过创建: {existing_video_files[0]}")
                
                # 写入标签（总是写入最新的标签）
                with open(txt_output_path, 'w', encoding='utf-8') as f:
                    f.write(caption)
                
                segments.append({
                    "index": segment_index,
                    "start_frame": current_frame,
                    "end_frame": segment_end,
                    "caption": caption,
                    "video_path": video_output_path,
                    "text_path": txt_output_path
                })
                
                logger.info(f"已保存片段 {segment_index+1}: {caption}")
                print(f"  已保存片段 {segment_index+1}: {filename}")
            
            current_frame += frames_per_segment
            segment_index += 1
            
        # 保存元数据
        metadata = {
            "source_video": video_path,
            "source_fps": float(fps),
            "processed_fps": float(effective_fps),
            "total_frames": len(processed_frames),
            "segments": segments
        }
        
        metadata_path = os.path.join(output_dir, "metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
            
        logger.info(f"视频处理完成: {video_path}，共生成 {len(segments)} 个片段")
        print(f"视频处理完成: {os.path.basename(video_path)}，共生成 {len(segments)} 个片段")

    def get_video_duration(self, video_path):
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

    def split_video_intelligently(self, input_path, output_dir, filename):
        """智能分割视频，尽量对半分且避免过小片段"""
        duration = self.get_video_duration(input_path)
        if duration <= 60:  # 1分钟=60秒
            print(f"{filename} 时长不足1分钟，无需分割")
            return []
        
        # 计算分割策略：尽量对半分，但确保每段不超过1分钟
        num_segments = max(2, math.ceil(duration / 60))  # 至少分成2段，每段不超过1分钟
        segment_duration = duration / num_segments
        
        # 如果分割后每段都小于30秒，则不进行分割
        if segment_duration < 30:
            print(f"{filename} 分割后片段太小，跳过分割")
            return []
        
        print(f"将 {filename} 分割为 {num_segments} 个片段，每段约{segment_duration/60:.1f}分钟")
        
        # 创建输出目录
        base_name = Path(filename).stem
        suffix = Path(filename).suffix
        
        split_files = []
        
        # 分割前n-1个片段
        for i in range(num_segments - 1):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration
            
            output_file = os.path.join(output_dir, f"{base_name}_part{i+1:02d}{suffix}")
            # 检查文件是否已存在
            if os.path.exists(output_file):
                print(f"  文件已存在，跳过分割: {os.path.basename(output_file)}")
            else:
                cmd = [
                    'ffmpeg', '-i', input_path,
                    '-ss', str(start_time), '-to', str(end_time),
                    '-c', 'copy', output_file
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"已生成: {os.path.basename(output_file)} ({end_time-start_time:.1f}秒)")
            split_files.append(output_file)
        
        # 处理最后一个片段
        start_time = (num_segments - 1) * segment_duration
        output_file = os.path.join(output_dir, f"{base_name}_part{num_segments:02d}{suffix}")
        # 检查文件是否已存在
        if os.path.exists(output_file):
            print(f"  文件已存在，跳过分割: {os.path.basename(output_file)}")
        else:
            cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(start_time),
                '-c', 'copy', output_file
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"已生成: {os.path.basename(output_file)} ({duration-start_time:.1f}秒)")
        split_files.append(output_file)
        
        return split_files

    def process_folder_for_splitting(self, input_folder):
        """处理指定文件夹中的所有视频文件并分割过长视频"""
        # 支持的视频格式
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v', '.3gp'}
        
        # 创建输出目录
        output_dir = os.path.join(input_folder, "split_videos")
        os.makedirs(output_dir, exist_ok=True)
        
        split_files = []
        
        # 获取所有视频文件
        video_files = [f for f in os.listdir(input_folder) 
                      if os.path.isfile(os.path.join(input_folder, f)) 
                      and Path(f).suffix.lower() in video_extensions]
        
        print(f"检测到 {len(video_files)} 个视频文件需要处理")
        
        # 遍历文件夹中的所有文件
        for i, filename in enumerate(video_files, 1):
            file_path = os.path.join(input_folder, filename)
            
            # 检查是否为文件且为视频格式
            if os.path.isfile(file_path) and Path(filename).suffix.lower() in video_extensions:
                print(f"[{i}/{len(video_files)}] 正在处理: {filename}")
                duration = self.get_video_duration(file_path)
                
                # 如果视频小于等于1分钟，直接复制到输出目录
                if duration <= 60:
                    output_file = os.path.join(output_dir, filename)
                    # 检查文件是否已存在
                    if os.path.exists(output_file):
                        print(f"  文件已存在，跳过复制: {filename}")
                    else:
                        shutil.copy2(file_path, output_file)
                    split_files.append(output_file)
                    print(f"  已复制: {filename} (无需分割)")
                else:
                    # 否则进行分割
                    files = self.split_video_intelligently(file_path, output_dir, filename)
                    split_files.extend(files)
        
        print(f"所有视频分割完成，分割文件保存在: {output_dir}")
        return output_dir, split_files

    def process_all_videos(self, input_folder):
        """处理文件夹中的所有视频"""
        # 先进行视频分割
        split_dir, split_files = self.process_folder_for_splitting(input_folder)
        
        # 如果有分割后的文件，则处理这些文件；否则处理原始文件
        if split_files:
            video_files = split_files
            processing_folder = split_dir
        else:
            video_files = self.get_video_files(input_folder)
            processing_folder = input_folder
        
        if not video_files:
            logger.info("未找到支持的视频文件")
            return
            
        logger.info(f"找到 {len(video_files)} 个视频文件")
        print(f"开始处理 {len(video_files)} 个视频文件...")
        
        for i, video_file in enumerate(video_files, 1):
            try:
                print(f"[{i}/{len(video_files)}] 正在处理: {os.path.basename(video_file)}")
                self.process_video(video_file)
                print(f"[{i}/{len(video_files)}] 完成处理: {os.path.basename(video_file)}")
            except Exception as e:
                logger.error(f"处理视频 {video_file} 时出错: {e}")
                print(f"[{i}/{len(video_files)}] 处理失败: {os.path.basename(video_file)} - {e}")

    def detect_file_types(self, folder):
        """检测文件夹中的文件类型"""
        video_files = []
        image_files = []
        
        # 添加支持的图片格式
        supported_image_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
        
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.path.isfile(file_path):
                if file.lower().endswith(self.supported_formats):
                    video_files.append(file_path)
                elif file.lower().endswith(supported_image_formats):
                    image_files.append(file_path)
        
        return video_files, image_files