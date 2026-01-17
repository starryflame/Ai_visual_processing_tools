# This is a method from class VideoTagger


def update_font(self):
    """更新所有控件的字体"""
    # 使用更现代的字体组合
    self.font = ("Microsoft YaHei", self.font_size)
    
    # 更新所有控件的字体
    self.load_btn.config(font=self.font)
    self.play_btn.config(font=self.font)
    self.prev_frame_btn.config(font=self.font)
    self.next_frame_btn.config(font=self.font)
    self.set_start_btn.config(font=self.font)
    self.set_end_btn.config(font=self.font)
    self.add_tag_btn.config(font=self.font)
    self.export_btn.config(font=self.font)
    self.frame_label.config(font=self.font)
    self.tag_listbox.config(font=self.font)
    self.tag_context_menu.config(font=self.font)
    self.fps_entry.config(font=self.font)
    # 更新AI相关控件字体
    self.ai_generate_btn.config(font=self.font)
    self.ai_prompt_entry.config(font=("Microsoft YaHei", max(8, self.font_size - 2)))
    # 更新预设相关控件字体
    self.add_preset_btn.config(font=self.font)
    self.preset_entry.config(font=self.font)
    self.preset_context_menu.config(font=self.font)
    
    # 更新标签文本的字体
    for widget in self.root.winfo_children():
        self.update_widget_font(widget)

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['update_font']
