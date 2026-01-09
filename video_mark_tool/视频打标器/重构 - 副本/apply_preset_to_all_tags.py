# This is a method from class VideoTagger
from tkinter import  messagebox

def apply_preset_to_all_tags(self):
    """将预设标签应用到所有已标记的视频片段标签开头"""
    if not hasattr(self, 'selected_preset_type'):
        return
        
    # 获取预设标签文本
    if self.selected_preset_type == "manual":
        preset_text = self.manual_presets[self.selected_preset_index]
    else:  # AI生成的预设
        preset_text = self.caption_presets[self.selected_preset_index]["caption"]
        
    if not preset_text:
        messagebox.showerror("错误", "预设标签为空")
        return
        
    # 确认操作
    if not messagebox.askyesno("确认", f"确定要将预设标签 '{preset_text}' 添加到所有已标记片段的标签开头吗？", parent=self.root):
        return
        
    # 应用预设标签到所有标记
    updated_count = 0
    for i, tag in enumerate(self.tags):
        original_tag = tag["tag"]
        # 如果标签开头还没有这个预设标签，则添加
        if not original_tag.startswith(preset_text):
            new_tag = preset_text + "\n" + original_tag
            self.tags[i]["tag"] = new_tag
            # 更新列表框显示
            self.tag_listbox.delete(i)
            self.tag_listbox.insert(i, f"帧 {tag['start']}-{tag['end']}: {new_tag}")
            updated_count += 1
            
    messagebox.showinfo("完成", f"已将预设标签应用到 {updated_count} 个标记片段", parent=self.root)
    
    # 更新标记可视化
    self.draw_tag_markers()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['apply_preset_to_all_tags']
