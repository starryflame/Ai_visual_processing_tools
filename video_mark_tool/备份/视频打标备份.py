import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading

class VideoTagger:
    def __init__(self, root):
        self.root = root
        self.root.title("视频打标器")
        # 设置初始窗口大小为1920x1080
        self.root.geometry("1080x1080")
        
        # 视频相关变量
        self.video_path = ""
        self.cap = None
        self.total_frames = 0
        self.fps = 0
        self.current_frame = 0
        self.playing = False
        
        # 标记相关变量
        self.start_frame = 0
        self.end_frame = 0
        self.tags = []  # 存储标记信息 [{start, end, tag_text}]
        
        # 预处理帧存储
        self.processed_frames = []  # 存储预处理的帧
        self.frames_loaded = False   # 标记是否已完成帧预处理
        
        # 导出设置
        self.export_fps = tk.StringVar(value="原始帧率")
        
        # 字体大小控制
        self.font_size = 10
        self.font = ("Arial", self.font_size)
        
        self.setup_ui()
        
    def setup_ui(self):
        # 顶部控制面板
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10, fill=tk.X, padx=20)
        
        self.load_btn = tk.Button(control_frame, text="加载视频", command=self.load_video, font=self.font)
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        self.play_btn = tk.Button(control_frame, text="播放/暂停", command=self.toggle_play, state=tk.DISABLED, font=self.font)
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.prev_frame_btn = tk.Button(control_frame, text="上一帧", command=self.prev_frame, state=tk.DISABLED, font=self.font)
        self.prev_frame_btn.pack(side=tk.LEFT, padx=5)
        
        self.next_frame_btn = tk.Button(control_frame, text="下一帧", command=self.next_frame, state=tk.DISABLED, font=self.font)
        self.next_frame_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加字体缩放按钮
        font_control_frame = tk.Frame(control_frame)
        font_control_frame.pack(side=tk.RIGHT, padx=5)
        
        tk.Label(font_control_frame, text="字体大小:", font=self.font).pack(side=tk.LEFT)
        self.font_decrease_btn = tk.Button(font_control_frame, text="-", command=self.decrease_font, width=3, font=self.font)
        self.font_decrease_btn.pack(side=tk.LEFT, padx=2)
        self.font_increase_btn = tk.Button(font_control_frame, text="+", command=self.increase_font, width=3, font=self.font)
        self.font_increase_btn.pack(side=tk.LEFT, padx=2)
        
        # 视频显示区域 - 使用grid布局以更好地适应窗口大小
        self.video_frame = tk.Frame(self.root, bg="black")
        self.video_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        self.video_label = tk.Label(self.video_frame, bg="black")
        self.video_label.pack(expand=True, fill=tk.BOTH)
        
        # 进度条和帧数显示
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(pady=10, fill=tk.X, padx=20)
        
        self.frame_label = tk.Label(progress_frame, text="帧: 0/0", font=self.font)
        self.frame_label.pack()
        
        # 创建带标记可视化的进度条框架
        self.progress_canvas = tk.Canvas(progress_frame, height=50)
        self.progress_canvas.pack(fill=tk.X, pady=5)
        
        # 修改进度条配置，增大滑块大小
        self.progress = tk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                command=self.on_progress_change, state=tk.DISABLED, showvalue=0,
                                width=20, length=300)  # 增加width和length参数
        self.progress.pack(fill=tk.X)
        
        # 标记控制面板
        tag_frame = tk.Frame(self.root)
        tag_frame.pack(pady=10, fill=tk.X, padx=20)
        
        self.set_start_btn = tk.Button(tag_frame, text="设置开始帧", command=self.set_start_frame, state=tk.DISABLED, font=self.font)
        self.set_start_btn.pack(side=tk.LEFT, padx=5)
        
        self.set_end_btn = tk.Button(tag_frame, text="设置结束帧", command=self.set_end_frame, state=tk.DISABLED, font=self.font)
        self.set_end_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Label(tag_frame, text="标签:", font=self.font).pack(side=tk.LEFT, padx=(20, 5))
        # 修改标签输入框为支持多行文本的文本框
        self.tag_entry = tk.Text(tag_frame, width=30, height=5, font=self.font)
        self.tag_entry.pack(side=tk.LEFT, padx=5)
        
        # 添加滚动条
        scrollbar = tk.Scrollbar(tag_frame, command=self.tag_entry.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tag_entry.config(yscrollcommand=scrollbar.set)
        
        self.add_tag_btn = tk.Button(tag_frame, text="添加标记", command=self.add_tag, state=tk.DISABLED, font=self.font)
        self.add_tag_btn.pack(side=tk.LEFT, padx=5)
        
        # 标记列表
        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(list_frame, text="已标记片段:", font=self.font).pack(anchor=tk.W)
        
        self.tag_listbox = tk.Listbox(list_frame, font=self.font)
        self.tag_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建右键菜单
        self.tag_context_menu = tk.Menu(self.tag_listbox, tearoff=0, font=self.font)
        self.tag_context_menu.add_command(label="编辑标签", command=self.edit_tag)
        self.tag_context_menu.add_command(label="删除标签", command=self.delete_tag)
        
        # 绑定右键点击事件
        self.tag_listbox.bind("<Button-3>", self.show_tag_context_menu)
        
        # 导出按钮和设置
        export_frame = tk.Frame(self.root)
        export_frame.pack(pady=10, fill=tk.X, padx=20)
        
        tk.Label(export_frame, text="导出帧率:", font=self.font).pack(side=tk.LEFT, padx=(0, 5))
        self.fps_entry = tk.Entry(export_frame, textvariable=self.export_fps, width=10, font=self.font)
        self.fps_entry.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = tk.Button(export_frame, text="导出所有标记片段", command=self.export_tags, state=tk.DISABLED, font=self.font)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self.on_window_resize)
        
    def load_video(self):
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv")]
        )
        
        if not file_path:
            return
            
        self.video_path = file_path
        
        # 释放之前的视频捕获对象
        if self.cap:
            self.cap.release()
            
        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0
        
        # 清空之前处理的帧
        self.processed_frames = []
        self.frames_loaded = False
        self.tags = []  # 清空标记
        self.tag_listbox.delete(0, tk.END)  # 清空列表框
        self.export_btn.config(state=tk.DISABLED)  # 禁用导出按钮
        
        # 更新UI状态
        self.progress.config(to=self.total_frames-1, state=tk.NORMAL)
        self.play_btn.config(state=tk.NORMAL)
        self.prev_frame_btn.config(state=tk.NORMAL)
        self.next_frame_btn.config(state=tk.NORMAL)
        self.set_start_btn.config(state=tk.NORMAL)
        self.set_end_btn.config(state=tk.NORMAL)
        self.add_tag_btn.config(state=tk.NORMAL)
        
        # 更新导出帧率选项
        self.export_fps.set(f"{self.fps:.2f}")
        
        # 预处理所有帧
        self.preprocess_frames()
        
    def preprocess_frames(self):
        """预处理所有视频帧并存储为图片"""
        if not self.cap:
            return
            
        # 显示加载提示和进度条
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("加载中")
        self.loading_window.geometry("300x100")
        self.loading_window.transient(self.root)
        self.loading_window.grab_set()  # 模态窗口
        
        tk.Label(self.loading_window, text="正在预处理视频帧，请稍候...", font=self.font).pack(pady=10)
        
        # 创建进度条
        self.loading_progress = ttk.Progressbar(self.loading_window, mode='determinate', length=200)
        self.loading_progress.pack(pady=10)
        self.loading_progress['maximum'] = self.total_frames
        
        # 显示进度百分比的标签
        self.loading_label = tk.Label(self.loading_window, text="0%", font=self.font)
        self.loading_label.pack()
        
        self.root.update()
        
        # 重新打开视频文件以确保从头开始
        self.cap.release()
        self.cap = cv2.VideoCapture(self.video_path)
        
        # 处理每一帧
        for i in range(self.total_frames):
            ret, frame = self.cap.read()
            if ret:
                # 转换颜色格式
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 将视频帧调整为720p以提高性能
                frame = self.resize_to_720p(frame)
                
                # 保持原始宽高比的情况下调整大小
                frame = self.resize_frame(frame, 800, 450)
                
                # 存储处理后的帧
                self.processed_frames.append(frame)
                
                # 更新进度条
                self.loading_progress['value'] = i + 1
                progress_percent = int((i + 1) / self.total_frames * 100)
                self.loading_label.config(text=f"{progress_percent}%")
                self.loading_window.update()
            else:
                break
                
        self.frames_loaded = True
        # 关闭加载窗口
        self.loading_window.destroy()
                
        # 显示第一帧
        self.show_frame()
        self.draw_tag_markers()  # 绘制标记可视化
        
    def show_frame(self):
        if not self.frames_loaded or not self.processed_frames:
            return
            
        if self.current_frame < len(self.processed_frames):
            frame = self.processed_frames[self.current_frame]
            
            # 转换为PIL Image并显示
            image = Image.fromarray(frame)
            photo = ImageTk.PhotoImage(image)
            
            self.video_label.config(image=photo)
            self.video_label.image = photo  # 保持引用
            
            # 更新进度条和帧数显示
            self.progress.set(self.current_frame)
            self.frame_label.config(text=f"帧: {self.current_frame}/{self.total_frames-1}")
            
    def draw_tag_markers(self):
        """在进度条上绘制标记段的可视化"""
        self.progress_canvas.delete("all")
        
        if self.total_frames <= 0:
            return
            
        canvas_width = self.progress_canvas.winfo_width()
        if canvas_width <= 1:  # 初始时可能为1
            canvas_width = self.progress.winfo_width()
            
        # 绘制整个时间轴
        self.progress_canvas.create_rectangle(0, 10, canvas_width, 20, fill="#ddd", outline="")
        
        # 定义多种颜色用于不同标记
        colors = ["blue", "red", "green", "orange", "purple", "brown", "pink", "gray", "olive", "cyan"]
        
        # 绘制每个标记段
        for i, tag in enumerate(self.tags):
            start_x = int((tag["start"] / self.total_frames) * canvas_width)
            end_x = int((tag["end"] / self.total_frames) * canvas_width)
            # 使用不同颜色并添加透明效果（通过宽度和轮廓实现视觉上的区分）
            color = colors[i % len(colors)]
            # 绘制半透明效果的标记
            self.progress_canvas.create_rectangle(start_x, 10, end_x, 20, fill=color, outline=color, stipple="gray50")
            # 在标记上显示序号
            if end_x - start_x > 20:  # 只有当标记足够宽时才显示文字
                self.progress_canvas.create_text((start_x + end_x) // 2, 15, text=str(i+1), fill="white", font=("Arial", 8))

        # 绘制当前帧位置指示器
        current_x = int((self.current_frame / self.total_frames) * canvas_width)
        self.progress_canvas.create_line(current_x, 0, current_x, 30, fill="red", width=2)
        
        # 绘制开始帧和结束帧标记
        if self.start_frame > 0:
            start_x = int((self.start_frame / self.total_frames) * canvas_width)
            self.progress_canvas.create_line(start_x, 5, start_x, 25, fill="green", width=2)
            self.progress_canvas.create_text(start_x, 0, text=f"开始:{self.start_frame}", anchor="n", fill="green")
            
        if self.end_frame > 0:
            end_x = int((self.end_frame / self.total_frames) * canvas_width)
            self.progress_canvas.create_line(end_x, 5, end_x, 25, fill="purple", width=2)
            self.progress_canvas.create_text(end_x, 0, text=f"结束:{self.end_frame}", anchor="n", fill="purple")
            
        # 绘制时间轴上的时间标记
        if self.fps > 0:
            # 绘制开始时间
            self.progress_canvas.create_text(5, 35, text="0s", anchor="w", fill="black")
            
            # 绘制结束时间
            total_time = self.total_frames / self.fps
            self.progress_canvas.create_text(canvas_width-5, 35, text=f"{total_time:.1f}s", anchor="e", fill="black")
            
            # 如果有开始帧，显示当前选择段的时间长度
            if self.start_frame > 0 and self.current_frame >= self.start_frame:
                selected_time = (self.current_frame - self.start_frame) / self.fps
                mid_x = int(((self.start_frame + self.current_frame) / 2 / self.total_frames) * canvas_width)
                self.progress_canvas.create_text(mid_x, 45, text=f"{selected_time:.2f}s", fill="blue")
                
    def on_progress_change(self, value):
        if not self.frames_loaded:
            return
            
        new_frame = int(float(value))
        
        # 如果已经设置了开始帧，限制不能拖动到开始帧之前
        if self.start_frame > 0 and new_frame < self.start_frame:
            self.current_frame = self.start_frame
            self.progress.set(self.start_frame)
        else:
            self.current_frame = new_frame
            
        self.show_frame()
        self.draw_tag_markers()
        
    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.play_video()
            
    def play_video(self):
        if not self.playing or not self.frames_loaded:
            return
            
        self.current_frame += 1
        if self.current_frame >= self.total_frames:
            self.current_frame = 0
            
        self.show_frame()
        self.draw_tag_markers()
        self.root.after(int(1000/self.fps), self.play_video)
        
    def prev_frame(self):
        if self.current_frame > 0:
            self.current_frame -= 1
            self.show_frame()
            self.draw_tag_markers()
            
    def next_frame(self):
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            self.show_frame()
            self.draw_tag_markers()
            
    def set_start_frame(self):
        self.start_frame = self.current_frame
        self.draw_tag_markers()  # 更新标记可视化
        
    def set_end_frame(self):
        self.end_frame = self.current_frame
        self.draw_tag_markers()  # 更新标记可视化
        
    def add_tag(self):
        # 修改获取标签文本的方式
        tag_text = self.tag_entry.get("1.0", tk.END).strip()
        if not tag_text:
            messagebox.showerror("错误", "请输入标签文本")
            return
            
        if self.start_frame > self.end_frame:
            messagebox.showerror("错误", "开始帧不能大于结束帧")
            return
            
        # 添加到标记列表
        tag_info = {
            "start": self.start_frame,
            "end": self.end_frame,
            "tag": tag_text
        }
        self.tags.append(tag_info)
        
        # 更新列表框
        self.tag_listbox.insert(tk.END, f"帧 {self.start_frame}-{self.end_frame}: {tag_text}")
        
        # 启用导出按钮（如果有至少一个标记）
        if len(self.tags) > 0:
            self.export_btn.config(state=tk.NORMAL)
        
        # 清空输入框
        self.tag_entry.delete("1.0", tk.END)
        
        # 清空已选中的开始和结束点
        self.start_frame = 0
        self.end_frame = 0
        
        # 更新标记可视化
        self.draw_tag_markers()
        
    def export_tags(self):
        if not self.tags:
            messagebox.showerror("错误", "没有标记需要导出")
            return
            
        # 选择导出目录
        export_dir = filedialog.askdirectory(title="选择导出目录")
        if not export_dir:
            return
            
        # 获取导出帧率
        try:
            if self.fps_entry.get() == "原始帧率":
                export_fps = self.fps
            else:
                export_fps = float(self.fps_entry.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效的帧率数值")
            return
            
        # 创建主文件夹
        main_folder = os.path.join(export_dir, "标记视频片段")
        os.makedirs(main_folder, exist_ok=True)
        
        # 导出每个标记片段
        for i, tag in enumerate(self.tags):
            start_frame = tag["start"]
            end_frame = tag["end"]
            tag_text = tag["tag"]
            
            # 获取第一帧来确定尺寸
            if start_frame < len(self.processed_frames):
                first_frame = self.processed_frames[start_frame]
                height, width = first_frame.shape[:2]
                
                # 生成文件名
                filename = f"video_{i+1:03d}_{tag_text}"
                video_path = os.path.join(main_folder, f"{filename}.mp4")
                txt_path = os.path.join(main_folder, f"{filename}.txt")
                
                # 视频写入器参数
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter(video_path, fourcc, export_fps, (width, height))
                
                # 写入视频帧
                for frame_num in range(start_frame, min(end_frame + 1, len(self.processed_frames))):
                    # 将RGB转换回BGR
                    frame_bgr = cv2.cvtColor(self.processed_frames[frame_num], cv2.COLOR_RGB2BGR)
                    out.write(frame_bgr)
                        
                out.release()
                
                # 创建标签文件
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(tag_text)
                
        messagebox.showinfo("完成", f"已导出 {len(self.tags)} 个标记片段到: {main_folder}")
        
    def resize_frame(self, frame, max_width, max_height):
        """
        保持宽高比的情况下调整帧大小
        """
        h, w = frame.shape[:2]
        
        # 计算宽高比
        aspect_ratio = w / h
        
        # 根据宽高比计算新的尺寸
        if w > max_width or h > max_height:
            if w / max_width > h / max_height:
                new_w = max_width
                new_h = int(max_width / aspect_ratio)
            else:
                new_h = max_height
                new_w = int(max_height * aspect_ratio)
        else:
            new_w, new_h = w, h
            
        # 调整帧大小
        resized_frame = cv2.resize(frame, (new_w, new_h))
        return resized_frame
        
        
    def resize_to_720p(self, frame):
        """
        将帧调整为720p分辨率以提高性能
        """
        h, w = frame.shape[:2]
        
        # 如果高度已经小于等于720，则不调整
        if h <= 720:
            return frame
            
        # 计算新尺寸保持宽高比
        new_height = 720
        new_width = int(w * (new_height / h))
        
        # 调整帧大小
        resized_frame = cv2.resize(frame, (new_width, new_height))
        return resized_frame
        
    def on_window_resize(self, event):
        """处理窗口大小变化事件"""
        if event.widget == self.root:  # 只处理主窗口的大小变化
            # 重新绘制标记可视化
            self.draw_tag_markers()
            
    def show_tag_context_menu(self, event):
        """显示标记列表的右键菜单"""
        # 检查是否有选中的项目
        selection = self.tag_listbox.curselection()
        if selection:
            self.tag_listbox.selection_clear(0, tk.END)
            self.tag_listbox.selection_set(selection[0])
            self.tag_context_menu.post(event.x_root, event.y_root)

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
        edit_window.geometry("400x300")  # 增大窗口尺寸
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # 将窗口居中显示
        edit_window.update_idletasks()
        x = (edit_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (edit_window.winfo_screenheight() // 2) - (300 // 2)
        edit_window.geometry(f"400x300+{x}+{y}")
        
        # 标签输入框
        tk.Label(edit_window, text="标签内容:", font=self.font).pack(pady=(20, 5))
        # 修改为支持多行文本的文本框
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
            # 修改获取标签文本的方式
            new_tag = tag_entry.get("1.0", tk.END).strip()
            if not new_tag:
                messagebox.showerror("错误", "请输入标签文本", parent=edit_window)
                return
                
            # 更新数据
            self.tags[index]["tag"] = new_tag
            
            # 更新列表框显示
            start_frame = self.tags[index]["start"]
            end_frame = self.tags[index]["end"]
            self.tag_listbox.delete(index)
            self.tag_listbox.insert(index, f"帧 {start_frame}-{end_frame}: {new_tag}")
            self.tag_listbox.selection_set(index)
            
            # 更新标记可视化
            self.draw_tag_markers()
            
            edit_window.destroy()
            
        def cancel_edit():
            edit_window.destroy()
            
        tk.Button(button_frame, text="保存", command=save_edit, font=self.font).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="取消", command=cancel_edit, font=self.font).pack(side=tk.LEFT, padx=5)
        
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
        
    def increase_font(self):
        """增大字体"""
        self.font_size += 1
        self.update_font()
        
    def decrease_font(self):
        """减小字体"""
        if self.font_size > 1:
            self.font_size -= 1
            self.update_font()
            
    def update_font(self):
        """更新所有控件的字体"""
        self.font = ("Arial", self.font_size)
        
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
        
        # 更新标签文本的字体
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
        
    def on_closing(self):
        if self.cap:
            self.cap.release()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTagger(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()