import os
import cv2
import numpy as np


def stretch_video_to_5_seconds(input_path, target_fps=16, target_duration=5):
    """
    加载视频，如果其时长小于目标时长，则将其放慢以达到目标时长，
    并设置固定的目标帧率。返回处理后的视频帧列表和实际FPS。
    
    Args:
        input_path (str): 输入视频文件的路径。
        target_fps (int): 目标帧率，默认为 16。
        target_duration (float): 目标时长（秒），默认为 5.
        
    Returns:
        tuple: (frames list, actual_fps) 处理后的视频帧列表和实际FPS，如果出错则返回 ([], 0)。
    """
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        print(f"  - 错误: 无法打开视频文件 {input_path}")
        return [], 0
    
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_original_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    original_duration = total_original_frames / original_fps if original_fps > 0 else 0

    print(f"正在处理: {os.path.basename(input_path)}")
    print(f"  - 原始时长: {original_duration:.2f} 秒")
    print(f"  - 原始帧率: {original_fps:.2f} fps")
    print(f"  - 总帧数: {total_original_frames}")

    if original_fps <= 0 or total_original_frames <= 0:
        print(f"  - 错误: 无法读取视频的持续时间或帧率。")
        cap.release()
        return [], 0

    # 如果视频本身已经大于等于目标时长，跳过
    if original_duration >= target_duration:
        print(f"  - 跳过: 视频时长 >= {target_duration} 秒。")
        # 读取视频帧并调整到目标帧率
        frames = []
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
            frame_count += 1
        
        cap.release()
        # 重新采样到目标帧率
        target_total_frames = target_fps * target_duration
        resampled_frames = resample_frames(frames, total_original_frames, int(target_total_frames))
        return resampled_frames, target_fps

    # 计算目标总帧数
    target_total_frames = target_fps * target_duration
    
    # 计算需要重复的帧数来达到目标时长
    # 为了将视频从 original_duration 拉伸到 target_duration，我们需要重复帧
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    
    cap.release()
    
    # 重复帧以达到目标持续时间
    stretched_frames = []
    if len(frames) > 0:
        # 计算每个原始帧应该重复多少次
        if total_original_frames > 0:
            repeat_factor = target_total_frames / total_original_frames
            for i, frame in enumerate(frames):
                # 根据位置计算应该重复的次数
                start_idx = int(i * repeat_factor)
                end_idx = int((i + 1) * repeat_factor)
                for _ in range(end_idx - start_idx):
                    stretched_frames.append(frame)
        
        # 确保帧数准确为目标帧数
        if len(stretched_frames) > target_total_frames:
            stretched_frames = stretched_frames[:int(target_total_frames)]
        elif len(stretched_frames) < target_total_frames:
            # 如果帧数不够，复制最后一帧
            last_frame = stretched_frames[-1] if stretched_frames else frames[-1] if frames else None
            if last_frame is not None:
                while len(stretched_frames) < target_total_frames:
                    stretched_frames.append(last_frame)

    print(f"  - 处理完成: 原始帧数 {len(frames)}, 目标帧数 {len(stretched_frames)}, 目标帧率 {target_fps} fps")
    
    return stretched_frames, target_fps


def resample_frames(frames, original_frame_count, target_frame_count):
    """
    重新采样帧列表以匹配目标帧数
    """
    if target_frame_count <= 0:
        return []
    
    if target_frame_count == original_frame_count:
        return frames[:]
    
    resampled = []
    for i in range(target_frame_count):
        idx = int(i * original_frame_count / target_frame_count)
        idx = min(idx, len(frames) - 1)  # 确保索引不越界
        resampled.append(frames[idx])
    
    return resampled


def save_video_with_opencv(frames, output_path, fps, width, height):
    """
    使用OpenCV保存视频帧到文件
    """
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        # 确保帧尺寸正确
        if frame.shape[0] != height or frame.shape[1] != width:
            frame = cv2.resize(frame, (width, height))
        out.write(frame)
    
    out.release()


def process_video_folder(folder_path):
    """
    处理文件夹中的视频，将时长小于5秒的视频通过重复帧扩展到5秒
    """
    # 获取文件夹中所有视频文件
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    video_files = []
    
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if any(file.lower().endswith(ext) for ext in video_extensions):
                video_files.append(os.path.join(root, file))
    
    for video_path in video_files:
        # 获取视频信息
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"无法打开视频: {video_path}")
            continue
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # 如果视频时长小于5秒，则进行处理
        if duration < 5:
            print(f"正在处理视频: {video_path} (原时长: {duration:.2f}s)")
            
            # 读取所有帧
            frames = []
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(frame)
            
            cap.release()
            
            # 计算目标总帧数
            target_fps = 16
            target_duration = 5
            target_total_frames = target_fps * target_duration
            
            # 通过重复帧的方式延长视频到5秒
            extended_frames = []
            if len(frames) > 0:
                # 计算每个原始帧应该重复多少次
                repeat_factor = target_total_frames / len(frames)
                
                for i, frame in enumerate(frames):
                    # 根据位置计算应该重复的次数
                    start_idx = int(i * repeat_factor)
                    end_idx = int((i + 1) * repeat_factor)
                    
                    # 添加帧副本
                    for _ in range(max(1, end_idx - start_idx)):
                        if len(extended_frames) < target_total_frames:
                            extended_frames.append(frame)
                
                # 如果帧数仍不足，用最后一帧填充
                while len(extended_frames) < target_total_frames and len(frames) > 0:
                    extended_frames.append(frames[-1])
                
                # 如果帧数超出，截断
                if len(extended_frames) > target_total_frames:
                    extended_frames = extended_frames[:target_total_frames]
            
            # 保存处理后的视频
            if extended_frames and len(extended_frames) > 0:
                temp_path = video_path + "_temp.mp4"
                
                # 获取原始视频的尺寸
                height, width = extended_frames[0].shape[:2]
                
                save_video_with_opencv(extended_frames, temp_path, target_fps, width, height)
                
                # 替换原始文件
                os.remove(video_path)
                os.rename(temp_path, video_path.replace('.tmp', '') if video_path.endswith('.tmp') else video_path)
                
                print(f"已保存处理后的视频: {video_path}")
            else:
                print(f"处理失败: {video_path}")
        else:
            print(f"跳过视频 (时长 >= 5s): {video_path}")
        
        # 释放cap资源
        cap.release()


def main():
    folder_path = input("请输入包含视频文件的文件夹路径: ")
    
    if not os.path.isdir(folder_path):
        print("错误: 指定的路径不是有效目录")
        return
    
    print(f"开始处理文件夹: {folder_path}")
    process_video_folder(folder_path)
    print("处理完成!")


if __name__ == "__main__":
    main()