import cv2
import os
import numpy as np
from pathlib import Path
from tqdm import tqdm
import argparse

class VideoShotDetector:
    def __init__(self, threshold=30, min_shot_duration=1.0):
        """
        初始化视频分镜检测器
        
        Args:
            threshold: 场景变化阈值 (默认30)
            min_shot_duration: 最小镜头持续时间(秒) (默认1.0秒)
        """
        self.threshold = threshold
        self.min_shot_duration = min_shot_duration
        self.shots = []
        
    def detect_shots(self, video_path, show_progress=True):
        """
        检测视频中的分镜点
        
        Args:
            video_path: 视频文件路径
            show_progress: 是否显示进度条
            
        Returns:
            list: 分镜时间点列表 [(start_frame, end_frame), ...]
        """
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"无法打开视频文件: {video_path}")
        
        # 获取视频信息
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        min_shot_frames = int(self.min_shot_duration * fps)
        
        print(f"视频信息:")
        print(f"  FPS: {fps}")
        print(f"  总帧数: {total_frames}")
        print(f"  最小镜头帧数: {min_shot_frames}")
        
        # 读取第一帧
        ret, prev_frame = cap.read()
        if not ret:
            cap.release()
            raise ValueError("无法读取视频第一帧")
        
        # 转换为灰度图并计算直方图
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        prev_hist = cv2.calcHist([prev_gray], [0], None, [256], [0, 256])
        prev_hist = cv2.normalize(prev_hist, prev_hist).flatten()
        
        shot_boundaries = [0]  # 第一个镜头从第0帧开始
        current_shot_start = 0
        
        # 进度条
        if show_progress:
            pbar = tqdm(total=total_frames, desc="检测分镜")
        
        frame_count = 1
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # 转换为灰度图并计算直方图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist = cv2.normalize(hist, hist).flatten()
            
            # 计算直方图差异
            diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA) * 100
            
            # 如果差异超过阈值且距离上一个镜头足够远，则认为是新的镜头
            if diff > self.threshold and (frame_count - current_shot_start) >= min_shot_frames:
                shot_boundaries.append(frame_count)
                current_shot_start = frame_count
            
            prev_hist = hist.copy()
            frame_count += 1
            
            if show_progress:
                pbar.update(1)
        
        if show_progress:
            pbar.close()
        
        # 添加最后一个镜头的结束点
        shot_boundaries.append(total_frames)
        
        # 创建镜头列表 [(start_frame, end_frame), ...]
        self.shots = []
        for i in range(len(shot_boundaries) - 1):
            start_frame = shot_boundaries[i]
            end_frame = shot_boundaries[i + 1]
            if end_frame - start_frame >= min_shot_frames:
                self.shots.append((start_frame, end_frame))
        
        cap.release()
        return self.shots
    
    def save_shots(self, video_path, output_dir, prefix="shot"):
        """
        保存所有分镜到指定目录
        
        Args:
            video_path: 原始视频文件路径
            output_dir: 输出目录
            prefix: 文件名前缀
        """
        if not self.shots:
            print("没有检测到分镜，请先运行detect_shots()")
            return
        
        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # 打开视频文件
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        print(f"\n开始保存分镜...")
        print(f"共检测到 {len(self.shots)} 个分镜")
        
        for i, (start_frame, end_frame) in enumerate(self.shots):
            # 设置视频读取位置到镜头开始处
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            
            # 创建输出文件路径
            output_filename = f"{prefix}_{i+1:03d}.mp4"
            output_path = os.path.join(output_dir, output_filename)
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            # 写入镜头的所有帧
            frames_to_write = end_frame - start_frame
            pbar = tqdm(total=frames_to_write, desc=f"保存分镜 {i+1}/{len(self.shots)}", leave=False)
            
            for frame_num in range(start_frame, end_frame):
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                pbar.update(1)
            
            pbar.close()
            out.release()
            
            # 计算镜头时长
            duration = (end_frame - start_frame) / fps
            print(f"  ✓ 已保存: {output_filename} ({duration:.2f}秒, {frames_to_write}帧)")
        
        cap.release()
        print(f"\n所有分镜已保存到: {os.path.abspath(output_dir)}")
    
    def print_shot_info(self, video_path):
        """
        打印分镜信息
        
        Args:
            video_path: 视频文件路径
        """
        if not self.shots:
            print("没有检测到分镜，请先运行detect_shots()")
            return
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        print(f"\n分镜信息:")
        print(f"{'序号':<6} {'起始帧':<10} {'结束帧':<10} {'起始时间':<12} {'结束时间':<12} {'时长(秒)':<10}")
        print("-" * 70)
        
        for i, (start_frame, end_frame) in enumerate(self.shots):
            start_time = start_frame / fps
            end_time = end_frame / fps
            duration = end_time - start_time
            
            print(f"{i+1:<6} {start_frame:<10} {end_frame:<10} "
                  f"{format_time(start_time):<12} {format_time(end_time):<12} {duration:<10.2f}")

def format_time(seconds):
    """格式化时间为 HH:MM:SS.ms 格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

def main():
    parser = argparse.ArgumentParser(description='视频自动分镜工具')
    parser.add_argument('input_video', help='输入视频文件路径')
    parser.add_argument('-o', '--output', default='shots_output', help='输出目录 (默认: shots_output)')
    parser.add_argument('-t', '--threshold', type=float, default=30.0, help='场景变化阈值 (默认: 30.0)')
    parser.add_argument('-m', '--min_duration', type=float, default=1.0, help='最小镜头时长(秒) (默认: 1.0)')
    parser.add_argument('-p', '--prefix', default='shot', help='输出文件前缀 (默认: shot)')
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input_video):
        print(f"错误: 输入文件不存在: {args.input_video}")
        return
    
    try:
        # 创建分镜检测器
        detector = VideoShotDetector(threshold=args.threshold, 
                                   min_shot_duration=args.min_duration)
        
        print(f"开始处理视频: {args.input_video}")
        
        # 检测分镜
        shots = detector.detect_shots(args.input_video)
        print(f"\n检测完成! 共找到 {len(shots)} 个分镜")
        
        # 显示分镜信息
        detector.print_shot_info(args.input_video)
        
        # 保存分镜
        detector.save_shots(args.input_video, args.output, args.prefix)
        
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")

if __name__ == "__main__":
    # 如果直接运行脚本而不是通过命令行参数
    if len(os.sys.argv) == 1:
        # 可以在这里设置默认参数进行测试
        input_video = input("请输入视频文件路径: ").strip()
        if os.path.exists(input_video):
            detector = VideoShotDetector(threshold=30.0, min_shot_duration=1.0)
            try:
                shots = detector.detect_shots(input_video)
                detector.print_shot_info(input_video)
                output_dir = "shots_output"
                detector.save_shots(input_video, output_dir, "shot")
            except Exception as e:
                print(f"错误: {str(e)}")
        else:
            print("文件不存在!")
    else:
        main()
