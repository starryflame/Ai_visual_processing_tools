# This is a method from class VideoTagger

import cv2

def resize_to_720p(self, frame):
    """
    将帧调整为720p分辨率以提高性能
    """
    # 从配置文件读取目标高度
    target_height = self.config.getint('PROCESSING', 'target_frame_height', fallback=720)
    
    h, w = frame.shape[:2]
    
    # 如果高度已经小于等于target_height，则不调整
    if h <= target_height:
        return frame
        
    # 计算新尺寸保持宽高比
    new_height = target_height
    new_width = int(w * (new_height / h))
    
    # 调整帧大小
    resized_frame = cv2.resize(frame, (new_width, new_height))
    return resized_frame

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['resize_to_720p']
