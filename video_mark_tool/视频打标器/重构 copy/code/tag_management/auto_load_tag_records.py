# This is a method from class VideoTagger
import os
import tkinter as tk


def auto_load_tag_records(self):
    """自动加载标记记录（在加载视频后调用）"""
    if not self.video_path:
        return
        
    # 生成记录文件路径
    record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
    
    if os.path.exists(record_file):
        try:
            import json
            with open(record_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 验证视频文件是否匹配
            if data.get("video_name") == os.path.basename(self.video_path):
                # 自动加载标记
                for tag in data.get("tags", []):
                    self.tags.append({
                        "start": tag["start"],
                        "end": tag["end"],
                        "tag": tag["tag"]
                    })
                    self.tag_listbox.insert(tk.END, f"帧 {tag['start']}-{tag['end']}: {tag['tag']}")
                
                # 更新UI状态
                if len(self.tags) > 0:
                    self.export_btn.config(state=tk.NORMAL)
                    
                # 更新标记可视化
                self.draw_tag_markers()
                
                print(f"自动加载了 {len(self.tags)} 个标记记录")
                
        except Exception as e:
            print(f"自动加载标记记录失败: {str(e)}")

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['auto_load_tag_records']
