import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
import numpy as np
import time

class VideoClipper:
    def __init__(self, root):
        self.root = root
        self.root.title("视频剪辑器")
        
        # 设置初始窗口大小
        window_width = 1200
        window_height = 1000
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 视频相关变量
        self.video_path = ""
        self.cap = None
        self.total_frames = 0
        self.fps = 0
        self.current_frame = 0
        self.playing = False
        self.play_thread = None
        
        # 剪辑相关变量
        self.start_frame = 0
        self.end_frame = 0
        
        # 帧缓存（预加载所有帧）
        self.frames_cache = []
        
        # 字体设置
        self.font = ("Microsoft YaHei", 10)
        self.button_font = ("Microsoft YaHei", 12, "bold")  # 按钮字体放大
        
        self.setup_ui()
        
    def setup_ui(self):
        """初始化主界面 UI 布局"""
        root = self.root
    
        # 设置整体网格权重
        for i in range(5):  # 改为 5 行（合并按钮行）
            root.grid_rowconfigure(i, weight=0 if i != 1 else 1)
        root.grid_columnconfigure(0, weight=1)
    
        # ===================【顶部控制栏】===================
        control_frame = tk.Frame(root)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.load_btn = tk.Button(control_frame, text="加载视频", command=self.load_video, font=self.button_font)
        self.load_btn.pack(side=tk.LEFT, padx=5)
    
        # ===================【视频展示区域】===================
        self.video_panel = tk.Frame(root, bg="black")
        self.video_panel.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        self.video_canvas = tk.Canvas(self.video_panel, bg="black")
        self.video_canvas.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    
        # ===================【播放控制与剪辑标记区（合并为一行）】===================
        control_frame = tk.Frame(root)
        control_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        
        # 播放控制按钮
        self.play_btn = tk.Button(control_frame, text="播放/暂停", command=self.toggle_play, state=tk.DISABLED, font=self.button_font)
        self.play_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.prev_frame_btn = tk.Button(control_frame, text="上一帧", command=self.prev_frame, state=tk.DISABLED, font=self.button_font)
        self.prev_frame_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.next_frame_btn = tk.Button(control_frame, text="下一帧", command=self.next_frame, state=tk.DISABLED, font=self.button_font)
        self.next_frame_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        # 剪辑标记按钮
        self.set_start_btn = tk.Button(control_frame, text="设置开始帧", command=self.set_start_frame, state=tk.DISABLED, font=self.button_font)
        self.set_start_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.set_end_btn = tk.Button(control_frame, text="设置结束帧", command=self.set_end_frame, state=tk.DISABLED, font=self.button_font)
        self.set_end_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.export_btn = tk.Button(control_frame, text="导出剪辑片段", command=self.export_clip, state=tk.DISABLED, font=self.button_font)
        self.export_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
    
        # ===================【进度条区域】===================
        progress_frame = tk.Frame(root)
        progress_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
    
        self.frame_label = tk.Label(progress_frame, text="帧：0/0", font=self.font)
        self.frame_label.pack()
    
        self.progress = tk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                 command=self.on_progress_change, state=tk.DISABLED, showvalue=0)
        self.progress.pack(fill=tk.X)
        
        # ===================【起止帧标记区域】===================
        self.marker_frame = tk.Frame(root)
        self.marker_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)
        
        self.marker_canvas = tk.Canvas(self.marker_frame, height=30, bg="white")
        self.marker_canvas.pack(fill=tk.X)
        
        self.start_marker_label = tk.Label(self.marker_frame, text="开始帧：0", font=self.font)
        self.start_marker_label.pack(side=tk.LEFT, padx=10)
        
        self.end_marker_label = tk.Label(self.marker_frame, text="结束帧：0", font=self.font)
        self.end_marker_label.pack(side=tk.RIGHT, padx=10)
    
        # ===================【全局事件绑定】===================
        self.root.bind('<space>', self.toggle_play_with_key)
        self.root.bind('<Key-a>', self.set_start_frame_key)
        self.root.bind('<Key-d>', self.set_end_frame_key)
        self.root.bind('<Key-Left>', self.prev_frame)
        self.root.bind('<Key-Right>', self.next_frame)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_video(self):
        """加载视频文件"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        
        self.video_path = file_path
        self.cap = cv2.VideoCapture(self.video_path)
        
        if not self.cap.isOpened():
            messagebox.showerror("错误", "无法打开视频文件")
            return
        
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        self.current_frame = 0
        self.start_frame = 0
        self.end_frame = self.total_frames - 1
        
        # 创建加载进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("加载视频中...")
        progress_window.geometry("300x100")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        progress_label = tk.Label(progress_window, text=f"加载进度：0/{self.total_frames}", font=self.font)
        progress_label.pack(pady=10)
        progress_bar = ttk.Progressbar(progress_window, length=250, mode='determinate')
        progress_bar.pack(pady=5)
        progress_bar["maximum"] = self.total_frames
        
        # 预加载所有帧到缓存（带进度显示）
        self.frames_cache = []
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        for i in range(self.total_frames):
            ret, frame = self.cap.read()
            if ret:
                self.frames_cache.append(frame)
            else:
                self.frames_cache.append(None)
            
            # 更新进度
            progress_label.config(text=f"加载进度：{i+1}/{self.total_frames}")
            progress_bar["value"] = i + 1
            if i % 10 == 0:
                self.root.update_idletasks()
        
        # 关闭进度窗口
        progress_window.destroy()
        
        # 更新 UI 状态
        self.play_btn.config(state=tk.NORMAL)
        self.prev_frame_btn.config(state=tk.NORMAL)
        self.next_frame_btn.config(state=tk.NORMAL)
        self.set_start_btn.config(state=tk.NORMAL)
        self.set_end_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)
        self.progress.config(state=tk.NORMAL, to=self.total_frames - 1)
        self.frame_label.config(text=f"帧：0/{self.total_frames - 1}")
        
        # 更新起止帧标记
        self.update_markers()
        
        self.show_frame(0)
        messagebox.showinfo("成功", f"视频加载成功\n总帧数：{self.total_frames}\n帧率：{self.fps} FPS")

    def update_markers(self):
        """更新进度条上的起止帧标记"""
        self.marker_canvas.delete("all")
        
        if self.total_frames <= 0:
            return
        
        canvas_width = self.marker_canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = 800
        
        # 计算每帧的像素宽度
        frame_width = canvas_width / self.total_frames
        
        # 绘制起始帧标记（绿色）
        start_x = self.start_frame * frame_width
        self.marker_canvas.create_line(start_x, 0, start_x, 30, fill="green", width=2)
        self.marker_canvas.create_text(start_x, 10, text="S", fill="green", font=("Arial", 8, "bold"), anchor=tk.N)
        
        # 绘制结束帧标记（红色）
        end_x = self.end_frame * frame_width
        self.marker_canvas.create_line(end_x, 0, end_x, 30, fill="red", width=2)
        self.marker_canvas.create_text(end_x, 10, text="E", fill="red", font=("Arial", 8, "bold"), anchor=tk.N)
        
        # 绘制剪辑区域背景（浅黄色）
        if self.start_frame < self.end_frame:
            self.marker_canvas.create_rectangle(start_x, 15, end_x, 25, fill="yellow", stipple="gray50")
        
        # 更新标签文本
        self.start_marker_label.config(text=f"开始帧：{self.start_frame}")
        self.end_marker_label.config(text=f"结束帧：{self.end_frame}")
        
        # 绑定 Canvas 大小变化事件
        self.marker_canvas.bind("<Configure>", lambda e: self.update_markers())

    def show_frame(self, frame_num):
        """显示指定帧"""
        if not self.frames_cache or frame_num >= len(self.frames_cache):
            return
        
        frame = self.frames_cache[frame_num]
        if frame is None:
            return
        
        # 转换颜色空间
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 获取画布尺寸
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 800
            canvas_height = 600
        
        # 计算缩放比例
        frame_height, frame_width = frame.shape[:2]
        scale = min(canvas_width / frame_width, canvas_height / frame_height)
        new_width = int(frame_width * scale)
        new_height = int(frame_height * scale)
        
        # 缩放图像
        frame = cv2.resize(frame, (new_width, new_height))
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        
        # 显示在画布中央
        self.video_canvas.delete("all")
        x = (canvas_width - new_width) // 2
        y = (canvas_height - new_height) // 2
        self.video_canvas.create_image(x, y, anchor=tk.NW, image=imgtk)
        self.video_canvas.image = imgtk
        
        # 更新帧号显示
        self.current_frame = frame_num
        self.frame_label.config(text=f"帧：{frame_num}/{self.total_frames - 1}")
        self.progress.set(frame_num)

    def toggle_play(self):
        """播放/暂停视频"""
        if self.playing:
            self.playing = False
            self.play_btn.config(text="播放")
        else:
            self.playing = True
            self.play_btn.config(text="暂停")
            self.play_thread = threading.Thread(target=self._play_video_thread, daemon=True)
            self.play_thread.start()

    def _play_video_thread(self):
        """播放视频线程"""
        while self.playing and self.current_frame < self.total_frames:
            if not self.frames_cache:
                break
            
            self.current_frame += 1
            if self.current_frame >= self.total_frames:
                self.current_frame = 0
                self.playing = False
                self.root.after(0, lambda: self.play_btn.config(text="播放"))
                break
            
            self.root.after(0, lambda f=self.current_frame: self.show_frame(f))
            time.sleep(1 / self.fps)

    def toggle_play_with_key(self, event):
        """空格键播放/暂停"""
        if self.play_btn['state'] == tk.NORMAL:
            self.toggle_play()

    def prev_frame(self, event=None):
        """上一帧"""
        if not self.frames_cache:
            return
        if self.current_frame > 0:
            self.show_frame(self.current_frame - 1)

    def next_frame(self, event=None):
        """下一帧"""
        if not self.frames_cache:
            return
        if self.current_frame < self.total_frames - 1:
            self.show_frame(self.current_frame + 1)

    def set_start_frame(self):
        """设置开始帧"""
        self.start_frame = self.current_frame
        self.update_markers()


    def set_end_frame(self):
        """设置结束帧"""
        self.end_frame = self.current_frame
        self.update_markers()


    def set_start_frame_key(self, event):
        """A 键设置开始帧"""
        if self.set_start_btn['state'] == tk.NORMAL:
            self.set_start_frame()

    def set_end_frame_key(self, event):
        """D 键设置结束帧"""
        if self.set_end_btn['state'] == tk.NORMAL:
            self.set_end_frame()

    def on_progress_change(self, value):
        """进度条改变事件"""
        if not self.frames_cache:
            return
        frame_num = int(float(value))
        self.show_frame(frame_num)

    def export_clip(self):
        """导出剪辑片段（替换原文件）"""
        if not self.frames_cache:
            messagebox.showerror("错误", "请先加载视频")
            return
        
        if self.start_frame >= self.end_frame:
            messagebox.showerror("错误", "开始帧必须小于结束帧")
            return
        
        # 确认导出（替换原文件）
        confirm = messagebox.askyesno("确认", 
            f"将保存第 {self.start_frame} 帧到第 {self.end_frame} 帧的视频片段\n"
            f"并替换原视频文件：{os.path.basename(self.video_path)}\n\n"
            f"此操作不可逆，是否继续？")
        if not confirm:
            return
        
        # 创建导出线程
        export_thread = threading.Thread(target=self._export_clip_thread, daemon=True)
        export_thread.start()

    def _export_clip_thread(self):
        """导出剪辑片段线程（替换原文件）"""
        progress_window = None
        temp_path = None
        
        try:
            # 释放原视频文件占用
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            # 获取视频目录和文件名
            video_dir = os.path.dirname(self.video_path)
            video_name = os.path.basename(self.video_path)
            
            # 创建临时文件名
            temp_path = os.path.join(video_dir, f"_temp_{video_name}")
            
            # 获取视频参数（从缓存中获取第一帧）
            if self.frames_cache and self.frames_cache[0] is not None:
                frame_height, frame_width = self.frames_cache[0].shape[:2]
            else:
                self.root.after(0, lambda: messagebox.showerror("错误", "无法获取视频参数！"))
                return
            
            fps = self.fps
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_path, fourcc, fps, (frame_width, frame_height))
            
            if not out.isOpened():
                self.root.after(0, lambda: messagebox.showerror("错误", "无法创建输出视频文件！"))
                return
            
            # 计算总帧数
            total_frames = self.end_frame - self.start_frame + 1
            
            # 创建进度窗口
            progress_window = tk.Toplevel(self.root)
            progress_window.title("保存视频中...")
            progress_window.geometry("300x100")
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            progress_label = tk.Label(progress_window, text=f"进度：0/{total_frames}", font=self.font)
            progress_label.pack(pady=10)
            progress_bar = ttk.Progressbar(progress_window, length=250, mode='determinate')
            progress_bar.pack(pady=5)
            progress_bar["maximum"] = total_frames
            
            # 从缓存写入指定帧区间
            frames_written = 0
            
            self.root.after(0, lambda: self.root.update())
            
            for frame_num in range(self.start_frame, self.end_frame + 1):
                if frame_num < len(self.frames_cache) and self.frames_cache[frame_num] is not None:
                    out.write(self.frames_cache[frame_num])
                    frames_written += 1
                    
                    # 更新进度
                    progress_label.config(text=f"进度：{frames_written}/{total_frames}")
                    progress_bar["value"] = frames_written
                    if frames_written % 10 == 0:
                        self.root.after(0, lambda: self.root.update())
            
            out.release()
            
            # 关闭进度窗口
            if progress_window:
                self.root.after(0, lambda: progress_window.destroy())
            
            if frames_written == 0:
                self.root.after(0, lambda: messagebox.showerror("错误", "未能写入任何帧！"))
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                return
            
            # 删除原文件，重命名临时文件（替换原视频）
            os.remove(self.video_path)
            os.rename(temp_path, self.video_path)
            
            # 重新加载视频
            self.root.after(0, lambda: self.load_video())
            
            # 更新 UI
            self.root.after(0, lambda: messagebox.showinfo("成功", 
                f"视频已保存并替换！\n{self.video_path}\n共保存 {frames_written} 帧"))
            
        except Exception as e:
            # 清理临时文件
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
            self.root.after(0, lambda: messagebox.showerror("错误", f"保存视频时出错:\n{str(e)}"))
        finally:
            # 确保进度窗口被关闭
            if progress_window:
                try:
                    self.root.after(0, lambda: progress_window.destroy())
                except:
                    pass

    def on_closing(self):
        """关闭窗口事件"""
        if self.cap is not None:
            self.cap.release()
        self.playing = False
        self.frames_cache = []
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoClipper(root)
    root.mainloop()