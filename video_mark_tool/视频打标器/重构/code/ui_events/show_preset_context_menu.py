# This is a method from class VideoTagger


def show_preset_context_menu(self, event, widget, preset_type, index):
    """显示预设标签的右键菜单"""
    # 保存当前选中的控件引用和类型信息
    self.selected_preset_widget = widget
    self.selected_preset_type = preset_type
    self.selected_preset_index = index
    self.preset_context_menu.post(event.x_root, event.y_root)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['show_preset_context_menu']
