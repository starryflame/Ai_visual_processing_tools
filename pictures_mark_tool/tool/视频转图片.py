import os
import cv2
from pathlib import Path
import argparse
from tqdm import tqdm
import logging
import sys

# 设置系统编码为utf-8，解决中文路径问题
if sys.platform.startswith('win'):
    import locale
    locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')

# 配置日志 - 使用UTF-8编码
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v'}

def is_video_file(file_path):
    """判断是否为视频文件"""
    return file_path.suffix.lower() in VIDEO_EXTENSIONS

def get_all_videos(folder_path):
    """递归获取文件夹中所有视频文件"""
    # 处理路径编码问题
    folder_path = Path(str(folder_path).encode('utf-8').decode('utf-8'))
    if not folder_path.exists():
        raise FileNotFoundError(f"文件夹不存在: {folder_path}")
    
    video_files = []
    for file_path in folder_path.rglob('*'):
        if file_path.is_file() and is_video_file(file_path):
            # 确保文件路径正确编码
            video_files.append(Path(str(file_path).encode('utf-8').decode('utf-8')))
    
    logger.info(f"找到 {len(video_files)} 个视频文件")
    for video in video_files:
        logger.info(f"  - {video}")
    return video_files

def extract_frames_from_video(video_path, output_folder, frames_per_second, start_index=0):
    """从单个视频中提取帧"""
    try:
        # 处理路径编码 - 移除重复的编码转换
        video_path = Path(video_path)
        output_folder = Path(output_folder)
        
        # 确保输出文件夹存在
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # 打开视频文件 - 直接使用Path对象
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            logger.warning(f"无法打开视频文件: {video_path}")
            return 0, start_index
        
        # 获取视频信息
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if video_fps == 0 or total_frames == 0:
            logger.warning(f"视频文件信息异常: {video_path}")
            cap.release()
            return 0, start_index
        
        logger.info(f"处理视频: {video_path}")
        logger.info(f"视频FPS: {video_fps:.2f}, 总帧数: {total_frames}")
        
        # 计算需要跳过的帧数
        skip_frames = max(1, int(round(video_fps / frames_per_second)))
        logger.info(f"每隔 {skip_frames} 帧提取一张图片")
        
        frame_count = 0
        saved_count = 0
        current_index = start_index
        
        # 显示进度条
        pbar = tqdm(total=total_frames, desc=f"提取 {video_path.name}", leave=False)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 每隔skip_frames帧保存一次
            if frame_count % skip_frames == 0:
                # 生成输出文件名 - 简化文件名处理逻辑
                safe_stem = "".join(c if c.isalnum() or c in (' ', '-', '_', '(', ')', '[', ']') or '\u4e00' <= c <= '\u9fff' else '_' for c in video_path.stem)
                # 限制文件名长度避免过长
                if len(safe_stem) > 50:
                    safe_stem = safe_stem[:50]
                output_filename = f"{safe_stem}_{current_index:06d}.png"
                output_path = output_folder / output_filename
                
                # 保存图片 - 使用cv2.imencode然后写入文件，避免直接imwrite的编码问题
                success, encoded_image = cv2.imencode('.png', frame)
                if success:
                    with open(str(output_path), 'wb') as f:
                        f.write(encoded_image)
                    saved_count += 1
                    current_index += 1
                    # 验证文件是否真的保存成功
                    if output_path.exists():
                        logger.debug(f"已保存: {output_filename}")
                    else:
                        logger.warning(f"文件可能未正确保存: {output_filename}")
                else:
                    logger.warning(f"编码失败: {output_filename}")
            
            frame_count += 1
            pbar.update(1)
        
        pbar.close()
        cap.release()
        
        logger.info(f"从 {video_path.name} 提取了 {saved_count} 张图片")
        return saved_count, current_index
        
    except Exception as e:
        logger.error(f"处理视频 {video_path} 时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0, start_index

def extract_frames_from_folder(input_folder, output_folder, frames_per_second):
    """从文件夹中所有视频提取帧"""
    # 处理路径编码
    input_folder = Path(str(input_folder).encode('utf-8').decode('utf-8'))
    output_folder = input_folder / str(output_folder).encode('utf-8').decode('utf-8')
    
    logger.info(f"输入文件夹: {input_folder.absolute()}")
    logger.info(f"输出文件夹: {output_folder.absolute()}")
    
    # 确保输出文件夹存在
    output_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"输出文件夹已创建: {output_folder}")
    
    # 获取所有视频文件
    try:
        video_files = get_all_videos(input_folder)
    except Exception as e:
        logger.error(f"搜索视频文件时出错: {e}")
        return
    
    if not video_files:
        logger.warning("未找到任何视频文件")
        return
    
    total_saved = 0
    current_index = 0
    
    logger.info(f"开始处理 {len(video_files)} 个视频文件...")
    
    # 处理每个视频文件
    for i, video_file in enumerate(video_files, 1):
        logger.info(f"[{i}/{len(video_files)}] 开始处理: {video_file}")
        saved_count, current_index = extract_frames_from_video(
            video_file, output_folder, frames_per_second, current_index
        )
        total_saved += saved_count
    
    # 最终检查
    final_files = list(output_folder.glob("*.png"))
    logger.info(f"处理完成！")
    logger.info(f"报告提取了 {total_saved} 张图片")
    logger.info(f"实际在输出文件夹中找到 {len(final_files)} 个png文件")
    
    if len(final_files) > 0:
        logger.info(f"前5个文件:")
        for file in final_files[:5]:
            logger.info(f"  - {file.name}")
    else:
        logger.warning("输出文件夹中没有找到图片文件，请检查是否有权限或磁盘空间问题")

# 新增：处理单个视频文件
def extract_frames_from_single_video(video_path, output_folder, frames_per_second):
    """从单个视频文件提取帧"""
    # 处理路径编码
    video_path = Path(str(video_path).encode('utf-8').decode('utf-8'))
    
    if not video_path.exists():
        logger.error(f"视频文件不存在: {video_path}")
        return
    
    if not is_video_file(video_path):
        logger.error(f"不是支持的视频文件格式: {video_path}")
        return
    
    # 如果输出文件夹是相对路径，则相对于视频文件所在目录创建
    if not Path(output_folder).is_absolute():
        output_folder = video_path.parent / str(output_folder).encode('utf-8').decode('utf-8')
    else:
        output_folder = Path(str(output_folder).encode('utf-8').decode('utf-8'))
    
    logger.info(f"输入视频: {video_path.absolute()}")
    logger.info(f"输出文件夹: {output_folder.absolute()}")
    
    # 确保输出文件夹存在
    output_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"输出文件夹已创建: {output_folder}")
    
    # 处理单个视频文件
    saved_count, _ = extract_frames_from_video(
        video_path, output_folder, frames_per_second, 0
    )
    
    # 最终检查
    final_files = list(output_folder.glob("*.png"))
    logger.info(f"处理完成！")
    logger.info(f"报告提取了 {saved_count} 张图片")
    logger.info(f"实际在输出文件夹中找到 {len(final_files)} 个png文件")
    
    if len(final_files) > 0:
        logger.info(f"前5个文件:")
        for file in final_files[:5]:
            logger.info(f"  - {file.name}")

def main():
    print("=== 视频帧提取工具 ===")
    
    # 获取用户输入 - 简化编码处理
    input_path = input("请输入视频文件或包含视频的文件夹路径: ").strip()
    
    if not input_path:
        print("错误: 必须指定输入路径")
        return
    
    try:
        frames_per_second = float(input("请输入每秒提取的图片数量 (例如: 1 表示每秒1张): "))
        if frames_per_second <= 0:
            print("错误: 提取频率必须大于0")
            return
    except ValueError:
        print("错误: 请输入有效的数字")
        return
    
    output_folder = input("请输入输出文件夹名称 (回车使用默认值 extracted_frames): ").strip()
    if not output_folder:
        output_folder = "extracted_frames"
    
    input_path_obj = Path(input_path)
    
    # 判断输入的是文件还是文件夹
    if input_path_obj.is_file():
        print(f"\n检测到输入的是单个视频文件")
        print(f"输出文件夹 '{output_folder}' 将创建在视频文件同级目录下")
        print("\n开始处理...")
        print("-" * 50)
        try:
            extract_frames_from_single_video(input_path, output_folder, frames_per_second)
        except Exception as e:
            logger.error(f"程序执行出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        print(f"\n检测到输入的是文件夹")
        print(f"输出文件夹 '{output_folder}' 将创建在输入文件夹内")
        print("\n开始处理...")
        print("-" * 50)
        try:
            extract_frames_from_folder(input_path, output_folder, frames_per_second)
        except Exception as e:
            logger.error(f"程序执行出错: {e}")
            import traceback
            logger.error(traceback.format_exc())

# 调试函数
def debug_check_paths():
    """调试路径相关问题"""
    print("=== 路径调试信息 ===")
    
    # 检查当前工作目录
    print(f"当前工作目录: {os.getcwd()}")
    
    # 检查常见的输出路径
    common_paths = [
        "extracted_frames",
        "./extracted_frames",
        os.path.join(os.getcwd(), "extracted_frames")
    ]
    
    for path in common_paths:
        p = Path(path)
        exists = p.exists()
        is_dir = p.is_dir() if exists else False
        print(f"路径 '{path}': 存在={exists}, 是目录={is_dir}")
        if exists and is_dir:
            files = list(p.glob("*"))
            print(f"  文件数量: {len(files)}")
            if files:
                print(f"  前3个文件: {[f.name for f in files[:3]]}")

if __name__ == "__main__":
    main()
    
    # 如果找不到文件，运行调试
    print("\n" + "="*50)
    #response = input("如果找不到输出文件，是否运行路径调试? (y/n): ")
    #if response.lower() == 'y':
    #    debug_check_paths()