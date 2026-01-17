# This is a method from class VideoTagger
from tkinter import messagebox


def delete_preset_tag(self):
    """删除预设标签"""
    if hasattr(self, 'selected_preset_widget') and hasattr(self, 'selected_preset_type'):
        if messagebox.askyesno("确认删除", "确定要删除这个预设标签吗？", parent=self.root):
            if self.selected_preset_type == "manual":
                # 从手动预设列表中删除
                del self.manual_presets[self.selected_preset_index]
                # 重新创建所有手动预设项显示
                for widget in self.preset_scrollable_frame.winfo_children():
                    widget.destroy()
                
                # 重新创建所有预设项显示
                for i, preset in enumerate(self.manual_presets):
                    self.create_manual_preset_item(i, preset)
                
                # 重新创建AI预设项显示
                for i, preset in enumerate(self.caption_presets):
                    self.create_preset_item(i, preset["caption"], preset["image"])
            else:
                # 从AI预设列表中删除
                del self.caption_presets[self.selected_preset_index]
                # 重新创建所有预设项显示
                for widget in self.preset_scrollable_frame.winfo_children():
                    widget.destroy()
                
                # 重新创建所有手动预设项显示
                for i, preset in enumerate(self.manual_presets):
                    self.create_manual_preset_item(i, preset)
                
                # 重新创建AI预设项显示
                for i, preset in enumerate(self.caption_presets):
                    self.create_preset_item(i, preset["caption"], preset["image"])
            
            # 清除引用避免错误
            del self.selected_preset_widget
            del self.selected_preset_type
            del self.selected_preset_index

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['delete_preset_tag']
