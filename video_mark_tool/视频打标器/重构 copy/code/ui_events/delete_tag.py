# This is a method from class VideoTagger
import tkinter as tk

def delete_tag(self):
    """删除选中的标签"""
    selection = self.tag_listbox.curselection()
    if not selection:
        return
        
    index = selection[0]
    
    # 从数据中删除
    del self.tags[index]
    
    # 从列表框中删除
    self.tag_listbox.delete(index)
    
    # 更新导出按钮状态
    if len(self.tags) == 0:
        self.export_btn.config(state=tk.DISABLED)
        
    # 更新标记可视化
    self.draw_tag_markers()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['delete_tag']
