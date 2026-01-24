# This is a method from class VideoTagger

import os
from tkinter import messagebox

def save_tag_records(self):
    """保存标记记录到文件"""
    if not self.video_path or not self.tags:
        messagebox.showerror("错误", "没有视频或标记需要保存")
        return
        
    # 生成记录文件路径（与视频同目录，同名但扩展名为.json）
    record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
    
    # 准备保存的数据
    data = {
        "video_path": self.video_path,
        "video_name": os.path.basename(self.video_path),
        "total_frames": self.total_frames,
        "fps": self.fps,
        "tags": self.tags,
        "excluded_segments": self.excluded_segments
    }
    
    try:
        import json
        with open(record_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("成功", f"标记记录已保存到: {record_file}")
    except Exception as e:
        messagebox.showerror("错误", f"保存标记记录失败: {str(e)}")

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['save_tag_records']
