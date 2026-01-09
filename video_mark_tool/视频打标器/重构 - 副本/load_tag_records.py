# This is a method from class VideoTagger
import os
import tkinter as tk
from tkinter import messagebox

def load_tag_records(self):
    """从文件加载标记记录"""
    if not self.video_path:
        messagebox.showerror("错误", "请先加载视频文件")
        return
        
    # 生成记录文件路径
    record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
    
    if not os.path.exists(record_file):
        messagebox.showerror("错误", f"未找到标记记录文件: {record_file}")
        return
        
    try:
        import json
        with open(record_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 验证视频文件是否匹配
        if data.get("video_name") != os.path.basename(self.video_path):
            if not messagebox.askyesno("警告", "记录文件与当前视频不匹配，是否仍要加载？"):
                return
                
        # 验证帧数是否匹配
        if data.get("total_frames") != self.total_frames:
            if not messagebox.askyesno("警告", "视频帧数与记录不匹配，是否仍要加载？"):
                return
        
        # 清空现有标记
        self.tags.clear()
        self.excluded_segments.clear()
        self.tag_listbox.delete(0, tk.END)
        
        # 加载标记
        for tag in data.get("tags", []):
            self.tags.append({
                "start": tag["start"],
                "end": tag["end"],
                "tag": tag["tag"]
            })
            self.tag_listbox.insert(tk.END, f"帧 {tag['start']}-{tag['end']}: {tag['tag']}")
            
        # 加载排除片段
        for segment in data.get("excluded_segments", []):
            self.excluded_segments.append({
                "start": segment["start"],
                "end": segment["end"]
            })
        
        # 更新UI状态
        if len(self.tags) > 0:
            self.export_btn.config(state=tk.NORMAL)
            
        # 更新标记可视化
        self.draw_tag_markers()
        
        messagebox.showinfo("成功", f"已加载 {len(self.tags)} 个标记记录")
        
    except Exception as e:
        messagebox.showerror("错误", f"加载标记记录失败: {str(e)}")

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['load_tag_records']
