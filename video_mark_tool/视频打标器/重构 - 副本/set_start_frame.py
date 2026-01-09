# This is a method from class VideoTagger


def set_start_frame(self):
    self.start_frame = self.current_frame
    
    # 自动设置结束帧为开始帧之后5秒的位置
    if self.fps > 0:
        # 从配置文件读取分段时长
        segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
        frames_5_seconds = int(segment_duration * self.fps)
        self.end_frame = min(self.current_frame + frames_5_seconds, self.total_frames - 1)
    else:
        # 如果无法获取FPS，则设置为开始帧后100帧
        self.end_frame = min(self.current_frame + 100, self.total_frames - 1)
        
    self.draw_tag_markers()  # 更新标记可视化

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['set_start_frame']
