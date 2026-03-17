# UI Events Module - UI 事件处理模块
# 包含键盘快捷键、按钮点击等事件处理

import tkinter as tk
from tkinter import messagebox


def clear_frame_marks(self):
    """清空开始帧和结束帧的标记"""
    self.start_frame = 0
    self.end_frame = 0
    self.draw_tag_markers()  # 更新标记可视化


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


def edit_tag(self):
    """编辑选中的标签"""
    selection = self.tag_listbox.curselection()
    if not selection:
        return
        
    index = selection[0]
    tag_info = self.tags[index]
    
    # 创建编辑窗口
    edit_window = tk.Toplevel(self.root)
    edit_window.title("编辑标签")
    edit_window.geometry("400x300")
    edit_window.transient(self.root)
    edit_window.grab_set()
    
    # 将窗口居中显示
    edit_window.update_idletasks()
    x = (edit_window.winfo_screenwidth() // 2) - (400 // 2)
    y = (edit_window.winfo_screenheight() // 2) - (300 // 2)
    edit_window.geometry(f"400x300+{x}+{y}")
    
    # 标签输入框
    tk.Label(edit_window, text="标签内容:", font=self.font).pack(pady=(20, 5))
    tag_entry = tk.Text(edit_window, width=40, height=8, font=self.font)
    tag_entry.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
    tag_entry.insert("1.0", tag_info["tag"])
    tag_entry.focus()
    
    # 添加滚动条
    scrollbar = tk.Scrollbar(edit_window, command=tag_entry.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tag_entry.config(yscrollcommand=scrollbar.set)
    
    # 按钮框架
    button_frame = tk.Frame(edit_window)
    button_frame.pack(pady=20)
    
    def save_edit():
        new_tag = tag_entry.get("1.0", tk.END).strip()
        if not new_tag:
            messagebox.showerror("错误", "请输入标签文本", parent=edit_window)
            return
            
        self.tags[index]["tag"] = new_tag
        
        start_frame = self.tags[index]["start"]
        end_frame = self.tags[index]["end"]
        self.tag_listbox.delete(index)
        self.tag_listbox.insert(index, f"帧 {start_frame}-{end_frame}: {new_tag}")
        self.tag_listbox.selection_set(index)
        
        self.draw_tag_markers()
        edit_window.destroy()
        
    def cancel_edit():
        edit_window.destroy()
        
    tk.Button(button_frame, text="保存", command=save_edit, font=self.font).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="取消", command=cancel_edit, font=self.font).pack(side=tk.LEFT, padx=5)


def show_tag_context_menu(self, event):
    """显示标记列表的右键菜单"""
    selection = self.tag_listbox.curselection()
    if selection:
        self.tag_listbox.selection_clear(0, tk.END)
        self.tag_listbox.selection_set(selection[0])
        self.tag_context_menu.post(event.x_root, event.y_root)


def show_preset_context_menu(self, event, widget, preset_type, index):
    """显示预设标签的右键菜单"""
    self.selected_preset_widget = widget
    self.selected_preset_type = preset_type
    self.selected_preset_index = index
    self.preset_context_menu.post(event.x_root, event.y_root)


def on_closing(self):
    if self.cap:
        self.cap.release()
    self.root.destroy()


def on_progress_change(self, value):
    if not self.frames_loaded:
        return
        
    new_frame = int(float(value))
    
    if self.start_frame > 0 and new_frame < self.start_frame:
        self.current_frame = self.start_frame
        self.progress.set(self.start_frame)
    else:
        self.current_frame = new_frame
        
    self.show_frame()
    self.draw_tag_markers()
    self.highlight_tag_for_current_frame()


def on_root_click(self, event):
    """处理根窗口的点击事件"""
    clicked_widget = event.widget
    if clicked_widget != self.tag_entry and clicked_widget != self.preset_entry and clicked_widget != self.ai_prompt_entry and clicked_widget != self.fps_entry:
        if not self.is_child_of(clicked_widget, self.tag_entry) and not self.is_child_of(clicked_widget, self.preset_entry) and not self.is_child_of(clicked_widget, self.ai_prompt_entry) and not self.is_child_of(clicked_widget, self.fps_entry):
            self.root.focus_set()
    elif clicked_widget == self.ai_prompt_entry:
        self.ai_prompt_entry.focus_set()
    elif clicked_widget == self.fps_entry:
        self.fps_entry.focus_set()


def decrease_font(self):
    """减小字体"""
    if self.font_size > 1:
        self.font_size -= 1
        self.update_font()


def increase_font(self):
    """增大字体"""
    self.font_size += 1
    self.update_font()


def update_font(self):
    """更新所有控件的字体"""
    self.font = ("Microsoft YaHei", self.font_size)
    
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
    self.ai_generate_btn.config(font=self.font)
    self.ai_prompt_entry.config(font=("Microsoft YaHei", max(8, self.font_size - 2)))
    self.add_preset_btn.config(font=self.font)
    self.preset_entry.config(font=self.font)
    self.preset_context_menu.config(font=self.font)
    
    for widget in self.root.winfo_children():
        self.update_widget_font(widget)


def update_widget_font(self, widget):
    """递归更新控件字体"""
    try:
        if isinstance(widget, (tk.Label, tk.Button, tk.Entry)):
            widget.config(font=self.font)
    except:
        pass
        
    for child in widget.winfo_children():
        self.update_widget_font(child)


def on_window_resize(self, event):
    """处理窗口大小变化事件"""
    if event.widget == self.root:
        self.draw_tag_markers()


def next_frame(self):
    if self.current_frame < self.total_frames - 1:
        self.current_frame += 1
        self.show_frame()
        self.draw_tag_markers()


def prev_frame(self):
    if self.current_frame > 0:
        self.current_frame -= 1
        self.show_frame()
        self.draw_tag_markers()


def toggle_play(self):
    self.playing = not self.playing
    if self.playing:
        self.play_video()


def toggle_play_with_key(self, event=None):
    """通过键盘空格键切换播放状态"""
    focused_widget = self.root.focus_get()
    if isinstance(focused_widget, (tk.Entry, tk.Text)):
        return "break"
    self.toggle_play()


def set_start_frame(self):
    self.start_frame = self.current_frame
    
    if self.fps > 0:
        segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
        frames_5_seconds = int(segment_duration * self.fps)
        self.end_frame = min(self.current_frame + frames_5_seconds, self.total_frames - 1)
    else:
        self.end_frame = min(self.current_frame + 100, self.total_frames - 1)
        
    self.draw_tag_markers()


def set_end_frame(self):
    self.end_frame = self.current_frame
    self.draw_tag_markers()


def set_start_frame_key(self, event=None):
    """通过键盘按键'a'设置开始帧"""
    focused_widget = self.root.focus_get()
    if isinstance(focused_widget, (tk.Entry, tk.Text)):
        return "break"
    if self.set_start_btn['state'] == 'normal':
        self.set_start_frame()


def set_end_frame_key(self, event=None):
    """通过键盘按键'd'设置结束帧"""
    focused_widget = self.root.focus_get()
    if isinstance(focused_widget, (tk.Entry, tk.Text)):
        return "break"
    if self.set_end_btn['state'] == 'normal':
        self.set_end_frame()


__all__ = [
    'clear_frame_marks',
    'delete_tag',
    'edit_tag',
    'show_tag_context_menu',
    'show_preset_context_menu',
    'on_closing',
    'on_progress_change',
    'on_root_click',
    'decrease_font',
    'increase_font',
    'update_font',
    'update_widget_font',
    'on_window_resize',
    'next_frame',
    'prev_frame',
    'toggle_play',
    'toggle_play_with_key',
    'set_start_frame',
    'set_end_frame',
    'set_start_frame_key',
    'set_end_frame_key'
]
