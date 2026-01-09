# This is a method from class VideoTagger


def on_root_click(self, event):
    """处理根窗口的点击事件，如果点击的不是输入框，则让输入框失去焦点"""
    # 检查点击的控件是否是输入框或者输入框的子控件
    clicked_widget = event.widget
    if clicked_widget != self.tag_entry and clicked_widget != self.preset_entry and clicked_widget != self.ai_prompt_entry and clicked_widget != self.fps_entry:
        # 检查是否是输入框的子控件（如滚动条等）
        if not self.is_child_of(clicked_widget, self.tag_entry) and not self.is_child_of(clicked_widget, self.preset_entry) and not self.is_child_of(clicked_widget, self.ai_prompt_entry) and not self.is_child_of(clicked_widget, self.fps_entry):
            self.root.focus_set()
    # 如果点击的是AI提示词输入框，确保它能获得焦点
    elif clicked_widget == self.ai_prompt_entry:
        self.ai_prompt_entry.focus_set()
    # 如果点击的是导出帧率输入框，确保它能获得焦点
    elif clicked_widget == self.fps_entry:
        self.fps_entry.focus_set()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['on_root_click']
