# This is a method from class VideoTagger
from tkinter import messagebox

def exclude_segment(self):
    """标记当前选中的片段为排除片段"""
    if self.start_frame == 0 and self.end_frame == 0:
        messagebox.showerror("错误", "请先设置开始帧和结束帧")
        return
        
    if self.start_frame > self.end_frame:
        messagebox.showerror("错误", "开始帧不能大于结束帧")
        return
        
    # 添加到排除片段列表
    segment_info = {
        "start": self.start_frame,
        "end": self.end_frame
    }
    self.excluded_segments.append(segment_info)
    
    # 清空已选中的开始和结束点
    self.start_frame = 0
    self.end_frame = 0
    
    # 更新标记可视化
    self.draw_tag_markers()
    
    messagebox.showinfo("成功", "已将选中片段标记为排除片段")

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['exclude_segment']
