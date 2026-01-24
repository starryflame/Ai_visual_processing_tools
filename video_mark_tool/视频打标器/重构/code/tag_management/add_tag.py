# This is a method from class VideoTagger
import tkinter as tk
from tkinter import messagebox

def add_tag(self):
    # 修改获取标签文本的方式
    tag_text = self.tag_entry.get("1.0", tk.END).strip()
        
    if self.start_frame >= self.end_frame:
        messagebox.showerror("错误", "开始帧不能大于等于结束帧")
        return
        
    # 添加到标记列表
    tag_info = {
        "start": self.start_frame,
        "end": self.end_frame,
        "tag": tag_text
    }
    self.tags.append(tag_info)
    self.regenerate_all_tags_btn.config(state=tk.NORMAL)
    # 更新列表框
    self.tag_listbox.insert(tk.END, f"帧 {self.start_frame}-{self.end_frame}: {tag_text}")
    
    # 启用导出按钮（如果有至少一个标记）
    if len(self.tags) > 0:
        self.export_btn.config(state=tk.NORMAL)
    
    # 清空输入框
    self.tag_entry.delete("1.0", tk.END)
    
    # 让输入框失去焦点，以便键盘快捷键可以正常使用
    self.root.focus_set()
    
    # 保存当前的结束帧位置
    end_position = self.end_frame
    
    # 清空已选中的开始和结束点
    self.start_frame = 0
    self.end_frame = 0
    
    # 更新标记可视化
    self.draw_tag_markers()
    
    # 将滑块移动到之前设置的结束帧位置
    self.current_frame = end_position
    self.progress.set(self.current_frame)
    self.show_frame()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['add_tag']
