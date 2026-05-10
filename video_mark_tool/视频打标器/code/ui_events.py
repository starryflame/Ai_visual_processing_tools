# UI Events Module - UI 事件处理模块
# 包含键盘快捷键、按钮点击等事件处理

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk


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

    # 更新标记可视化
    self.draw_tag_markers()


def show_tag_context_menu(self, event):
    """显示标记列表的右键菜单"""
    selection = self.tag_listbox.curselection()
    if selection:
        self.tag_listbox.selection_clear(0, tk.END)
        self.tag_listbox.selection_set(selection[0])
        self.tag_context_menu.post(event.x_root, event.y_root)


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


def regenerate_tag_caption(self):
    """AI 重新生成选中片段的标签内容"""
    selection = self.tag_listbox.curselection()
    if not selection:
        return

    index = selection[0]
    tag_info = self.tags[index]
    start_frame = tag_info["start"]
    end_frame = tag_info["end"]
    current_caption = tag_info["tag"]

    # 检查是否有时频数据
    if not hasattr(self, 'processed_frames') or not self.processed_frames:
        messagebox.showerror("错误", "请先加载视频")
        return

    # 创建弹出窗口
    win = tk.Toplevel(self.root)
    win.title("AI 重新生成标签")
    win.geometry("900x700")
    win.transient(self.root)
    win.grab_set()
    win.update_idletasks()
    x = (win.winfo_screenwidth() // 2) - (900 // 2)
    y = (win.winfo_screenheight() // 2) - (700 // 2)
    win.geometry(f"900x700+{x}+{y}")

    # 顶部标签信息
    info_frame = tk.Frame(win)
    info_frame.pack(fill=tk.X, padx=10, pady=(10, 0))
    tk.Label(info_frame, text=f"片段帧范围: {start_frame} - {end_frame}", font=self.font).pack(anchor=tk.W)

    # 视频播放区域
    video_frame = tk.Frame(win)
    video_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    canvas = tk.Canvas(video_frame, bg='black')
    canvas.pack(fill=tk.BOTH, expand=True)

    # 播放控制变量
    is_playing = True
    current_frame_idx = start_frame
    play_task_id = None
    current_photo = [None]

    def play_video():
        nonlocal current_frame_idx, is_playing, play_task_id
        if not is_playing:
            return

        if current_frame_idx > end_frame:
            current_frame_idx = start_frame

        try:
            frame = self.processed_frames[current_frame_idx]
            image_obj = Image.fromarray(frame)
            max_w = canvas.winfo_width() - 10 if canvas.winfo_width() > 10 else 880
            max_h = canvas.winfo_height() - 10 if canvas.winfo_height() > 10 else 400
            image_obj.thumbnail((max_w, max_h), Image.LANCZOS)
            photo = ImageTk.PhotoImage(image_obj)
            canvas.delete("all")
            canvas.create_image(max_w // 2, max_h // 2, image=photo)
            current_photo[0] = photo

            fps = getattr(self, 'fps', 25) or 25
            play_task_id = canvas.after(int(1000 / fps), play_video)
        except Exception:
            pass

        current_frame_idx += 1

    # 初始显示第一帧
    try:
        first_frame = self.processed_frames[start_frame]
        image_obj = Image.fromarray(first_frame)
        image_obj.thumbnail((880, 400), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image_obj)
        canvas.create_image(440, 200, image=photo)
        current_photo[0] = photo
    except Exception:
        pass

    # 启动播放
    play_video()

    # 标签内容显示
    caption_frame = tk.Frame(win, height=200)
    caption_frame.pack(fill=tk.BOTH, padx=10, pady=(0, 10))
    caption_frame.pack_propagate(False)

    tk.Label(caption_frame, text="标签内容:", font=self.font).pack(anchor=tk.W)

    text_frame = tk.Frame(caption_frame)
    text_frame.pack(fill=tk.BOTH, expand=True)

    caption_text = tk.Text(text_frame, wrap=tk.WORD, font=self.font)
    caption_text.insert(tk.END, current_caption)
    caption_text.config(state=tk.NORMAL)

    scrollbar = tk.Scrollbar(text_frame, command=caption_text.yview)
    caption_text.config(yscrollcommand=scrollbar.set)
    caption_text.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    text_frame.grid_rowconfigure(0, weight=1)
    text_frame.grid_columnconfigure(0, weight=1)

    # 按钮框架
    button_frame = tk.Frame(win)
    button_frame.pack(fill=tk.X, padx=10, pady=10)

    # AI 重新生成按钮
    ai_regenerate_btn = tk.Button(button_frame, text="AI 重新生成", font=self.font, state=tk.NORMAL)
    ai_regenerate_btn.pack(side=tk.LEFT, padx=5)

    # 应用按钮
    def apply_caption():
        new_text = caption_text.get("1.0", tk.END).strip()
        if not new_text:
            messagebox.showerror("错误", "标签内容不能为空", parent=win)
            return
        self.tags[index]["tag"] = new_text
        self.tag_listbox.delete(index)
        self.tag_listbox.insert(index, f"帧 {start_frame}-{end_frame}: {new_text}")
        self.tag_listbox.selection_set(index)
        self.draw_tag_markers()
        win.destroy()

    apply_btn = tk.Button(button_frame, text="应用", command=apply_caption, font=self.font)
    apply_btn.pack(side=tk.LEFT, padx=5)

    # 取消按钮
    cancel_btn = tk.Button(button_frame, text="取消", command=win.destroy, font=self.font)
    cancel_btn.pack(side=tk.LEFT, padx=5)

    # AI 重新生成处理（在后台线程中运行）
    def do_ai_regenerate():
        ai_regenerate_btn.config(state=tk.DISABLED, text="AI 生成中...")
        caption_text.insert(tk.END, "\n\n[正在使用 AI 重新生成标签，请稍候...]")

        # 保存帧范围
        reg_start_frame = start_frame
        reg_end_frame = end_frame
        reg_index = index
        reg_win = win
        reg_btn = ai_regenerate_btn
        reg_text = caption_text
        reg_self = self

        def ai_thread():
            try:
                from ai_features import LLMClient
                llm_client = LLMClient(reg_self.config)
                frames = llm_client.extract_frames(reg_self.processed_frames, reg_start_frame, reg_end_frame)
                user_prompt = reg_self.ai_prompt_entry.get("1.0", tk.END).strip()
                new_caption = llm_client.generate_caption(frames, user_prompt)

                def update_ui():
                    reg_text.delete("1.0", tk.END)
                    reg_text.insert(tk.END, new_caption)
                    reg_btn.config(state=tk.NORMAL, text="AI 重新生成")

                reg_self.root.after(0, update_ui)

            except Exception as e:
                def show_error():
                    messagebox.showerror("错误", f"AI 标签生成失败：{str(e)}", parent=reg_win)
                    reg_btn.config(state=tk.NORMAL, text="AI 重新生成")

                reg_self.root.after(0, show_error)

        import threading
        threading.Thread(target=ai_thread, daemon=True).start()

    ai_regenerate_btn.config(command=do_ai_regenerate)

    # 窗口关闭时停止播放
    def on_closing():
        nonlocal is_playing
        is_playing = False
        if play_task_id is not None:
            canvas.after_cancel(play_task_id)
        win.destroy()

    win.protocol("WM_DELETE_WINDOW", on_closing)


__all__ = [
    'clear_frame_marks',
    'delete_tag',
    'show_tag_context_menu',
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
    'set_end_frame_key',
    'regenerate_tag_caption',
]
