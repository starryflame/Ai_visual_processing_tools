"""
工具函数模块
提供文件信息获取等辅助功能
"""
import os
import cv2


def get_image_info(image_path):
    """获取图片的分辨率信息"""
    try:
        img = cv2.imread(image_path)
        if img is not None:
            height, width, channels = img.shape
            return f"{width}x{height} ({channels} channels)"
        else:
            from PIL import Image
            pil_img = Image.open(image_path)
            width, height = pil_img.size
            return f"{width}x{height} ({pil_img.mode})"
    except Exception as e:
        return f"Error reading image: {str(e)}"


def get_video_info(video_path):
    """获取视频的分辨率、帧率和总帧数信息"""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return "无法打开视频文件"

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        cap.release()

        resolution = f"{width}x{height}"
        fps_str = f"{fps:.2f}fps" if fps > 0 else "unknown fps"
        frames_str = f"{total_frames} frames" if total_frames > 0 else "unknown frames"

        return f"{resolution}, {fps_str}, {frames_str}"
    except Exception as e:
        return f"Error reading video: {str(e)}"


def find_label_file(media_file, media_full_path):
    """
    查找媒体文件对应的标签文件

    Args:
        media_file: 媒体文件相对路径
        media_full_path: 媒体文件完整路径

    Returns:
        标签文件完整路径，如果不存在则返回 None
    """
    label_extensions = ['.txt', '.xml', '.json', '.csv']
    media_dir = os.path.dirname(media_full_path)
    base_name = os.path.splitext(os.path.basename(media_file))[0]

    for ext in label_extensions:
        potential_file = base_name + ext
        potential_path = os.path.join(media_dir, potential_file)
        if os.path.exists(potential_path):
            return potential_path

    return None


def delete_label_file(media_file, media_full_path):
    """
    删除媒体文件对应的标签文件

    Args:
        media_file: 媒体文件相对路径
        media_full_path: 媒体文件完整路径

    Returns:
        (成功删除的标签文件数, 错误信息列表)
    """
    label_extensions = ['.txt', '.xml', '.json', '.csv']
    media_dir = os.path.dirname(media_full_path)
    base_name = os.path.splitext(os.path.basename(media_file))[0]

    deleted_count = 0
    errors = []

    for ext in label_extensions:
        label_file = base_name + ext
        label_path = os.path.join(media_dir, label_file)
        if os.path.exists(label_path):
            try:
                os.remove(label_path)
                deleted_count += 1
            except Exception as e:
                errors.append(f"无法删除标签文件 {label_file}: {str(e)}")

    return deleted_count, errors
