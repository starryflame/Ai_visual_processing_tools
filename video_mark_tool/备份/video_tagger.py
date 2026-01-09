import cv2
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import threading
import torch
from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
import numpy as np
import configparser
import base64
import time
class VideoTagger:
    def __init__(self, root):
        self.root = root
        self.root.title("视频打标器")
        
        # 读取配置文件
        self.config = configparser.ConfigParser()
        # 修改读取配置文件的方式，显式指定编码为utf-8
        self.config.read('config.ini', encoding='utf-8')
        
        # 设置初始窗口大小
        window_width = self.config.getint('UI', 'window_width', fallback=1080)
        window_height = self.config.getint('UI', 'window_height', fallback=1080)
        self.root.geometry(f"{window_width}x{window_height}")
        
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
        self.excluded_segments = []  # 存储排除的片段 [{start, end}]
        
        # 预处理帧存储
        self.processed_frames = []  # 存储预处理的帧
        self.frames_loaded = False   # 标记是否已完成帧预处理
        
        # 导出设置
        default_fps = self.config.get('VIDEO', 'default_export_fps', fallback="原始帧率")
        self.export_fps = tk.StringVar(value=default_fps)
        
        # 字体大小控制
        self.font_size = 10
        # 修改默认字体为更现代的字体
        self.font = ("Microsoft YaHei", self.font_size)
        
        # 新增模型相关变量
        self.model_loaded = False
        self.qwen_model = None
        self.processor = None
        self.tokenizer = None
        self.caption_presets = []  # 存储模型生成的标签预设
        self.manual_presets = []   # 存储手动添加的标签预设
        
        # 拖拽调整大小相关变量
        self.drag_data = {"x": 0, "widget": None}
        
        self.setup_ui()
        
    def setup_ui(self):
        # 顶部控制面板
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10, fill=tk.X, padx=20)
        
        # 主要内容框架，使用可调整大小的窗格
        self.main_paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=10, sashrelief=tk.RAISED)
        self.main_paned_window.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # 右侧标签预设区域 (原左侧控制面板位置)
        self.preset_panel = tk.Frame(self.main_paned_window, width=150, bg="lightblue")
        self.main_paned_window.add(self.preset_panel)
        # 添加最小尺寸约束
        self.main_paned_window.paneconfig(self.preset_panel, minsize=150)
        
        preset_header = tk.Frame(self.preset_panel)
        preset_header.pack(fill=tk.X, pady=5)
        tk.Label(preset_header, text="标签预设:", font=self.font).pack(anchor=tk.W, padx=5)
        
        # 标签预设列表 - 使用带滚动条的画布来显示预设项
        preset_canvas_frame = tk.Frame(self.preset_panel)
        preset_canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preset_canvas = tk.Canvas(preset_canvas_frame)
        scrollbar = tk.Scrollbar(preset_canvas_frame, orient="vertical", command=self.preset_canvas.yview)
        self.preset_scrollable_frame = tk.Frame(self.preset_canvas)
        
        self.preset_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.preset_canvas.configure(
                scrollregion=self.preset_canvas.bbox("all")
            )
        )
        
        self.preset_canvas.create_window((0, 0), window=self.preset_scrollable_frame, anchor="nw")
        self.preset_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.preset_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 创建预设标签右键菜单
        self.preset_context_menu = tk.Menu(self.root, tearoff=0, font=self.font)  # 修改父组件为root
        self.preset_context_menu.add_command(label="编辑预设", command=self.edit_preset_tag)
        self.preset_context_menu.add_command(label="删除预设", command=self.delete_preset_tag)
        # 添加新功能：将预设标签应用到所有标记片段
        self.preset_context_menu.add_command(label="应用到所有标记", command=self.apply_preset_to_all_tags)
        
        # 中间视频显示区域
        self.video_panel = tk.Frame(self.main_paned_window, width=900, bg="black")
        self.main_paned_window.add(self.video_panel)
        # 添加最小尺寸约束
        self.main_paned_window.paneconfig(self.video_panel, minsize=500)
        
        # 修改：创建一个固定大小的画布来显示视频，确保画面完整显示
        self.video_canvas = tk.Canvas(self.video_panel, bg="black", width=800, height=600)
        self.video_canvas.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        # 左侧控制面板 (原右侧标签预设区域位置)
        self.control_panel = tk.Frame(self.main_paned_window, width=150, bg="lightgray")
        self.main_paned_window.add(self.control_panel)
        # 添加最小尺寸约束
        self.main_paned_window.paneconfig(self.control_panel, minsize=100)
        
        # 重新组织控制面板的布局，使用网格布局替代堆叠布局
        self.load_btn = tk.Button(self.control_panel, text="加载视频", command=self.load_video, font=self.font)
        self.load_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        self.play_btn = tk.Button(self.control_panel, text="播放/暂停", command=self.toggle_play, state=tk.DISABLED, font=self.font)
        self.play_btn.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        # 创建一个包含上一帧和下一帧按钮的框架
        frame_nav_frame = tk.Frame(self.control_panel, bg="lightgray")
        frame_nav_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        
        self.prev_frame_btn = tk.Button(frame_nav_frame, text="上一帧", command=self.prev_frame, state=tk.DISABLED, font=self.font)
        self.prev_frame_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.next_frame_btn = tk.Button(frame_nav_frame, text="下一帧", command=self.next_frame, state=tk.DISABLED, font=self.font)
        self.next_frame_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # 创建一个包含帧标记按钮的框架
        frame_mark_frame = tk.Frame(self.control_panel, bg="lightgray")
        frame_mark_frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        
        self.set_start_btn = tk.Button(frame_mark_frame, text="设置开始帧", command=self.set_start_frame, state=tk.DISABLED, font=self.font)
        self.set_start_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        self.set_end_btn = tk.Button(frame_mark_frame, text="设置结束帧", command=self.set_end_frame, state=tk.DISABLED, font=self.font)
        self.set_end_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # 添加清空开始和结束帧的按钮
        self.clear_frames_btn = tk.Button(self.control_panel, text="清空帧标记", command=self.clear_frame_marks, state=tk.DISABLED, font=self.font)
        self.clear_frames_btn.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        
        # 添加AI生成标签按钮
        self.ai_generate_btn = tk.Button(self.control_panel, text="AI生成标签", command=self.generate_ai_caption, state=tk.DISABLED, font=self.font)
        self.ai_generate_btn.grid(row=5, column=0, padx=5, pady=5, sticky="ew")
        
        # 添加AI提示词输入框
        ai_prompt_frame = tk.Frame(self.control_panel, bg="lightgray")
        ai_prompt_frame.grid(row=6, column=0, padx=5, pady=5, sticky="ew")
        tk.Label(ai_prompt_frame, text="AI提示词:", font=self.font, bg="lightgray").pack(anchor=tk.W)
        self.ai_prompt_entry = tk.Text(ai_prompt_frame, height=4, font=("Arial", 8))
        self.ai_prompt_entry.pack(fill=tk.X, pady=5)
        # 设置默认提示词
        self.ai_prompt_entry.insert("1.0", "详细描述视频画面。")
        # 确保输入框可编辑并能获得焦点
        self.ai_prompt_entry.config(state=tk.NORMAL, takefocus=True)
        # 绑定点击事件以确保能获得焦点

        # 添加字体缩放按钮
        font_control_frame = tk.Frame(self.control_panel, bg="lightgray")
        font_control_frame.grid(row=7, column=0, padx=5, pady=5, sticky="ew")
        
        tk.Label(font_control_frame, text="字体大小:", font=self.font, bg="lightgray").pack(side=tk.LEFT)
        self.font_decrease_btn = tk.Button(font_control_frame, text="-", command=self.decrease_font, width=3, font=self.font)
        self.font_decrease_btn.pack(side=tk.LEFT, padx=2)
        self.font_increase_btn = tk.Button(font_control_frame, text="+", command=self.increase_font, width=3, font=self.font)
        self.font_increase_btn.pack(side=tk.LEFT, padx=2)
        
        # 配置控制面板的网格列权重
        self.control_panel.columnconfigure(0, weight=1)
        
        # 标签预设操作按钮
        preset_btn_frame = tk.Frame(self.preset_panel)
        preset_btn_frame.pack(fill=tk.X, pady=5)
        
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
        
        # 修改：将操作类按钮移到右侧
        
        # 修改：将标签相关的控件放在左侧
        tk.Label(tag_frame, text="标签:", font=self.font).pack(side=tk.LEFT, padx=(20, 5))
        # 修改标签输入框为支持多行文本的文本框
        self.tag_entry = tk.Text(tag_frame, width=60, height=5, font=self.font)
        self.tag_entry.pack(side=tk.LEFT, padx=5)
        
        # 添加滚动条
        scrollbar = tk.Scrollbar(tag_frame, command=self.tag_entry.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tag_entry.config(yscrollcommand=scrollbar.set)
        
        self.add_tag_btn = tk.Button(tag_frame, text="添加标记", command=self.add_tag, state=tk.DISABLED, font=self.font)
        self.add_tag_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加排除片段按钮
        self.exclude_segment_btn = tk.Button(tag_frame, text="排除片段", command=self.exclude_segment, state=tk.DISABLED, font=self.font)
        self.exclude_segment_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加自动分段并AI识别按钮
        self.auto_segment_btn = tk.Button(tag_frame, text="自动分段AI识别", command=self.auto_segment_and_recognize, state=tk.DISABLED, font=self.font)
        self.auto_segment_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加预设标签输入框和按钮
        self.preset_entry = tk.Entry(tag_frame, width=15, font=self.font)
        self.preset_entry.pack(side=tk.LEFT, padx=5)
        
        self.add_preset_btn = tk.Button(tag_frame, text="添加预设", command=self.add_preset_tag, font=self.font)
        self.add_preset_btn.pack(side=tk.LEFT, padx=5)
        
        # 标记列表
        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=10, fill=tk.BOTH, expand=True, padx=20)
        
        tk.Label(list_frame, text="已标记片段:", font=self.font).pack(anchor=tk.W)
        
        # 减少标签列表框的高度，从默认的较大尺寸改为较小尺寸
        self.tag_listbox = tk.Listbox(list_frame, font=self.font, height=6)
        self.tag_listbox.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建右键菜单
        self.tag_context_menu = tk.Menu(self.tag_listbox, tearoff=0, font=self.font)
        self.tag_context_menu.add_command(label="编辑标签", command=self.edit_tag)
        self.tag_context_menu.add_command(label="删除标签", command=self.delete_tag)
        
        # 绑定右键点击事件
        self.tag_listbox.bind("<Button-3>", self.show_tag_context_menu)
        # 移除了对preset_listbox的绑定，因为已替换为文本框
        
        # 导出按钮和设置
        export_frame = tk.Frame(self.root)
        export_frame.pack(pady=10, fill=tk.X, padx=20)
        
        tk.Label(export_frame, text="导出帧率:", font=self.font).pack(side=tk.LEFT, padx=(0, 5))
        self.fps_entry = tk.Entry(export_frame, textvariable=self.export_fps, width=10, font=self.font)
        self.fps_entry.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = tk.Button(export_frame, text="导出所有标记片段", command=self.export_tags, state=tk.DISABLED, font=self.font)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        # 添加保存和加载标记记录的按钮
        self.save_record_btn = tk.Button(export_frame, text="保存标记记录", command=self.save_tag_records, state=tk.DISABLED, font=self.font)
        self.save_record_btn.pack(side=tk.LEFT, padx=5)
        
        self.load_record_btn = tk.Button(export_frame, text="加载标记记录", command=self.load_tag_records, state=tk.DISABLED, font=self.font)
        self.load_record_btn.pack(side=tk.LEFT, padx=5)
        
        # 绑定窗口大小变化事件
        self.root.bind('<Configure>', self.on_window_resize)
        # 绑定键盘事件，空格键控制播放/暂停
        self.root.bind('<space>', self.toggle_play_with_key)
        # 绑定键盘事件，a键设置开始帧，d键设置结束帧
        self.root.bind('<Key-a>', self.set_start_frame_key)
        self.root.bind('<Key-d>', self.set_end_frame_key)
        # 绑定鼠标点击事件，实现点击输入框外失去焦点
        self.root.bind('<Button-1>', self.on_root_click)

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

    def is_child_of(self, child, parent):
        """检查一个控件是否是另一个控件的子控件"""
        while child is not None:
            if child == parent:
                return True
            try:
                child = child.master
            except:
                break
        return False

    def toggle_play_with_key(self, event=None):
        """通过键盘空格键切换播放状态"""
        # 检查焦点是否在输入控件上，如果是则不处理
        focused_widget = self.root.focus_get()
        if isinstance(focused_widget, (tk.Entry, tk.Text)):
            return "break"  # 不处理该事件
        self.toggle_play()
        
    def set_start_frame_key(self, event=None):
        """通过键盘按键'a'设置开始帧"""
        # 检查焦点是否在输入控件上，如果是则不处理
        focused_widget = self.root.focus_get()
        if isinstance(focused_widget, (tk.Entry, tk.Text)):
            return "break"  # 不处理该事件
        if self.set_start_btn['state'] == 'normal':  # 只有按钮可用时才执行
            self.set_start_frame()
            
    def set_end_frame_key(self, event=None):
        """通过键盘按键'd'设置结束帧"""
        # 检查焦点是否在输入控件上，如果是则不处理
        focused_widget = self.root.focus_get()
        if isinstance(focused_widget, (tk.Entry, tk.Text)):
            return "break"  # 不处理该事件
        if self.set_end_btn['state'] == 'normal':  # 只有按钮可用时才执行
            self.set_end_frame()

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
            # 确保标记位置不会完全位于边缘之外
            start_x = max(2, int((tag["start"] / self.total_frames) * canvas_width))
            end_x = min(canvas_width-2, int((tag["end"] / self.total_frames) * canvas_width))
            # 使用不同颜色并添加透明效果（通过宽度和轮廓实现视觉上的区分）
            color = colors[i % len(colors)]
            # 绘制半透明效果的标记
            self.progress_canvas.create_rectangle(start_x, 10, end_x, 20, fill=color, outline=color, stipple="gray50")
            # 在标记上显示序号
            if end_x - start_x > 20:  # 只有当标记足够宽时才显示文字
                self.progress_canvas.create_text((start_x + end_x) // 2, 15, text=str(i+1), fill="white", font=("Arial", 8))
                
        # 绘制排除片段（用红色显示）
        for segment in self.excluded_segments:
            start_x = max(2, int((segment["start"] / self.total_frames) * canvas_width))
            end_x = min(canvas_width-2, int((segment["end"] / self.total_frames) * canvas_width))
            self.progress_canvas.create_rectangle(start_x, 10, end_x, 20, fill="red", outline="red", stipple="gray25")

        # 绘制当前帧位置指示器 (确保在可视区域内)
        current_x = max(1, min(canvas_width-1, int((self.current_frame / self.total_frames) * canvas_width)))
        self.progress_canvas.create_line(current_x, 0, current_x, 30, fill="red", width=2)
        
        # 绘制开始帧和结束帧标记 (确保在可视区域内)
        if self.start_frame > 0:
            start_x = max(1, min(canvas_width-1, int((self.start_frame / self.total_frames) * canvas_width)))
            self.progress_canvas.create_line(start_x, 5, start_x, 25, fill="green", width=2)
            # 调整文本位置避免被遮挡
            text_x = start_x
            if start_x < 30:  # 如果太靠近左边
                text_x = start_x + 25
                anchor = "w"
            elif start_x > canvas_width - 30:  # 如果太靠近右边
                text_x = start_x - 25
                anchor = "e"
            else:
                anchor = "n"
            self.progress_canvas.create_text(text_x, 5, text=f"开始:{self.start_frame}", anchor=anchor, fill="green", font=("Arial", 8))
            
        if self.end_frame > 0:
            end_x = max(1, min(canvas_width-1, int((self.end_frame / self.total_frames) * canvas_width)))
            self.progress_canvas.create_line(end_x, 5, end_x, 25, fill="purple", width=2)
            # 调整文本位置避免被遮挡
            text_x = end_x
            if end_x < 30:  # 如果太靠近左边
                text_x = end_x + 25
                anchor = "w"
            elif end_x > canvas_width - 30:  # 如果太靠近右边
                text_x = end_x - 25
                anchor = "e"
            else:
                anchor = "n"
            self.progress_canvas.create_text(text_x, 25, text=f"结束:{self.end_frame}", anchor=anchor, fill="purple", font=("Arial", 8))
            
        # 绘制时间轴上的时间标记
        if self.fps > 0:
            # 绘制开始时间
            self.progress_canvas.create_text(5, 35, text="0s", anchor="w", fill="black", font=("Arial", 8))
            
            # 绘制结束时间
            total_time = self.total_frames / self.fps
            self.progress_canvas.create_text(canvas_width-5, 35, text=f"{total_time:.1f}s", anchor="e", fill="black", font=("Arial", 8))
            
            # 如果有开始帧，显示当前选择段的时间长度
            if self.start_frame > 0 and self.current_frame >= self.start_frame:
                selected_time = (self.current_frame - self.start_frame) / self.fps
                mid_x = int(((self.start_frame + self.current_frame) / 2 / self.total_frames) * canvas_width)
                # 确保文本在可视范围内
                mid_x = max(20, min(canvas_width-20, mid_x))
                self.progress_canvas.create_text(mid_x, 45, text=f"{selected_time:.2f}s", fill="blue", font=("Arial", 8))
                
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
        self.highlight_tag_for_current_frame()  # 添加这一行来高亮当前帧对应的标签
        
    def highlight_tag_for_current_frame(self):
        """高亮显示当前帧对应的标签行"""
        # 清除之前的高亮
        self.tag_listbox.selection_clear(0, tk.END)
        
        # 查找当前帧所在的标记区间
        for i, tag in enumerate(self.tags):
            if tag["start"] <= self.current_frame <= tag["end"]:
                # 高亮对应的标签行
                self.tag_listbox.selection_set(i)
                # 确保该项在可视区域内
                self.tag_listbox.see(i)
                break
                
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
        
        # 自动设置结束帧为开始帧之后5秒的位置
        if self.fps > 0:
            frames_5_seconds = int(5 * self.fps)
            self.end_frame = min(self.current_frame + frames_5_seconds, self.total_frames - 1)
        else:
            # 如果无法获取FPS，则设置为开始帧后100帧
            self.end_frame = min(self.current_frame + 100, self.total_frames - 1)
            
        self.draw_tag_markers()  # 更新标记可视化
        
    def set_end_frame(self):
        self.end_frame = self.current_frame
        self.draw_tag_markers()  # 更新标记可视化
        
    def clear_frame_marks(self):
        """清空开始帧和结束帧的标记"""
        self.start_frame = 0
        self.end_frame = 0
        self.draw_tag_markers()  # 更新标记可视化
        
    def generate_ai_caption(self):
        """使用AI模型生成当前选中视频片段的标签"""
        try:
            # 检查是否安装了必要的库
            import torch
            from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
        except ImportError as e:
            messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 transformers 和 torch 库")
            return
        
        # 检查是否已设置开始帧和结束帧
        if self.start_frame == 0 and self.end_frame == 0:
            messagebox.showerror("错误", "请先设置开始帧和结束帧")
            return
            
        # 显示选择调用方式的窗口
        method_window = tk.Toplevel(self.root)
        method_window.title("选择AI调用方式")
        method_window.geometry("300x150")
        method_window.transient(self.root)
        method_window.grab_set()
        
        # 居中显示
        method_window.update_idletasks()
        x = (method_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (method_window.winfo_screenheight() // 2) - (150 // 2)
        method_window.geometry(f"300x150+{x}+{y}")
        
        tk.Label(method_window, text="请选择AI调用方式:", font=self.font).pack(pady=10)
        
        method_var = tk.StringVar(value="local")
        
        tk.Radiobutton(method_window, text="本地模型", variable=method_var, value="local", font=self.font).pack(anchor=tk.W, padx=30)
        tk.Radiobutton(method_window, text="vLLM API", variable=method_var, value="vllm", font=self.font).pack(anchor=tk.W, padx=30)
        
        def confirm_method():
            method = method_var.get()
            method_window.destroy()
            if method == "local":
                self._generate_ai_caption_local()
            else:
                self._generate_ai_caption_vllm()
        
        tk.Button(method_window, text="确定", command=confirm_method, font=self.font).pack(pady=10)
        
    def _generate_ai_caption_local(self):
        """使用本地模型生成标签"""
        # 显示加载提示
        loading_window = tk.Toplevel(self.root)
        loading_window.title("AI处理中")
        loading_window.geometry("300x100")
        loading_window.transient(self.root)
        loading_window.grab_set()
        
        # 将窗口居中显示
        loading_window.update_idletasks()
        x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
        loading_window.geometry(f"300x100+{x}+{y}")
        
        tk.Label(loading_window, text="正在加载模型并生成标签...", font=self.font).pack(pady=20)
        self.root.update()
        
        try:
            # 检查模型是否已加载
            if not self.model_loaded:
                # 从配置文件读取模型路径
                model_path = self.config.get('MODEL', 'qwen_vl_model_path', fallback=r"J:\models\LLM\Qwen-VL\Qwen3-VL-4B-Instruct")
                
                if not os.path.exists(model_path):
                    messagebox.showerror("错误", f"模型路径不存在: {model_path}\n请确认模型已下载并放置在正确位置")
                    loading_window.destroy()
                    return
                
                # 从配置文件读取模型精度设置
                torch_dtype_str = self.config.get('MODEL', 'torch_dtype', fallback='fp32')
                if torch_dtype_str == 'fp16':
                    torch_dtype = torch.float16
                elif torch_dtype_str == 'bf16':
                    torch_dtype = torch.bfloat16
                else:
                    torch_dtype = torch.float32
                
                # 加载模型
                self.model = AutoModelForVision2Seq.from_pretrained(
                    model_path,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch_dtype
                ).eval()
                self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
                self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
                self.model_loaded = True
            
            # 获取选中的视频片段帧
            if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
                # 从处理后的帧中提取视频片段
                frames = []
                # 从配置文件读取采样帧数
                max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
                
                # 采样最多max_sample_frames帧以提高性能
                total_frames = self.end_frame - self.start_frame + 1
                sample_count = min(max_sample_frames, total_frames)
                
                if total_frames <= sample_count:
                    indices = list(range(self.start_frame, self.end_frame + 1))
                else:
                    indices = np.linspace(self.start_frame, self.end_frame, sample_count, dtype=int)
                
                for i in indices:
                    if i < len(self.processed_frames):
                        # 转换为PIL Image
                        frame_rgb = self.processed_frames[i]
                        pil_frame = Image.fromarray(frame_rgb)
                        frames.append(pil_frame)
                
                # 如果只有一帧，复制以满足视频处理要求
                if len(frames) == 1:
                    frames.append(frames[0])
                
                # 获取用户自定义的提示词
                user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                if not user_prompt:
                    user_prompt = "详细描述视频画面"
                
                # 构建对话
                conversation = [{
                    "role": "user",
                    "content": [
                        {"type": "video", "video": frames},
                        {"type": "text", "text": user_prompt}
                    ]
                }]
                
                # 应用模板
                text_prompt = self.processor.apply_chat_template(
                    conversation,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                # 处理输入
                inputs = self.processor(
                    text=text_prompt,
                    videos=[frames],
                    return_tensors="pt"
                )
                
                # 移动到设备
                inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
                
                # 从配置文件读取生成参数
                max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=1024)
                temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.6)
                top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
                
                # 生成输出
                with torch.no_grad():
                    outputs = self.model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=True,
                        temperature=temperature,
                        top_p=top_p
                    )
                
                # 解码输出
                input_ids_len = inputs["input_ids"].shape[1]
                caption = self.tokenizer.decode(
                    outputs[0, input_ids_len:],
                    skip_special_tokens=True
                )
                caption = caption.strip()
                
                # 添加到预设列表
                # 使用第一帧作为缩略图
                thumbnail_frame = self.processed_frames[self.start_frame].copy()
                self.caption_presets.append({
                    "caption": caption,
                    "image": thumbnail_frame
                })
                
                # 创建新的预设项显示
                self.create_preset_item(len(self.caption_presets) - 1, caption, thumbnail_frame)
                
                messagebox.showinfo("成功", f"AI已生成标签并添加到预设列表:\n\n{caption}")
            else:
                messagebox.showerror("错误", "无法获取选中的视频片段")
                
        except Exception as e:
            messagebox.showerror("错误", f"AI标签生成失败: {str(e)}")
        finally:
            loading_window.destroy()

    def _generate_ai_caption_vllm(self):
        """使用vLLM API生成标签"""
        try:
            from openai import OpenAI
        except ImportError as e:
            messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 openai 库")
            return
            
        # 显示加载提示
        loading_window = tk.Toplevel(self.root)
        loading_window.title("AI处理中")
        loading_window.geometry("300x100")
        loading_window.transient(self.root)
        loading_window.grab_set()
        
        # 将窗口居中显示
        loading_window.update_idletasks()
        x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
        loading_window.geometry(f"300x100+{x}+{y}")
        
        tk.Label(loading_window, text="正在通过vLLM API生成标签...", font=self.font).pack(pady=20)
        self.root.update()
        
        try:
            # 从配置文件读取API设置
            api_base_url = self.config.get('VLLM', 'api_base_url', fallback="http://127.0.0.1:8000/v1")
            api_key = self.config.get('VLLM', 'api_key', fallback="EMPTY")
            model_name = self.config.get('VLLM', 'model_name', fallback="/models/Qwen3-VL-8B-Instruct")
            
            # 配置客户端
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            # 获取选中的视频片段帧
            if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
                # 从处理后的帧中提取视频片段
                frames = []
                # 从配置文件读取采样帧数
                max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
                
                # 采样最多max_sample_frames帧以提高性能
                total_frames = self.end_frame - self.start_frame + 1
                sample_count = min(max_sample_frames, total_frames)
                
                if total_frames <= sample_count:
                    indices = list(range(self.start_frame, self.end_frame + 1))
                else:
                    indices = np.linspace(self.start_frame, self.end_frame, sample_count, dtype=int)
                
                # 转换帧为base64格式
                frame_data_urls = []
                for i in indices:
                    if i < len(self.processed_frames):
                        # 转为 JPEG 并编码为 base64
                        frame_bgr = cv2.cvtColor(self.processed_frames[i], cv2.COLOR_RGB2BGR)
                        _, buffer = cv2.imencode(".jpg", frame_bgr)
                        encoded = base64.b64encode(buffer).decode("utf-8")
                        data_url = f"data:image/jpeg;base64,{encoded}"
                        frame_data_urls.append(data_url)
                
                # 如果只有一帧，复制以满足视频处理要求
                if len(frame_data_urls) == 1:
                    frame_data_urls.append(frame_data_urls[0])
                
                # 获取用户自定义的提示词
                user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                if not user_prompt:
                    user_prompt = "详细描述视频画面"
                
                # 构造消息：文本 + 多张图片
                content_list = [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
                
                # 添加所有帧
                for url in frame_data_urls:
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })
                
                messages = [{"role": "user", "content": content_list}]
                
                # 从配置文件读取生成参数
                max_tokens = self.config.getint('VLLM', 'max_tokens', fallback=1024)
                temperature = self.config.getfloat('VLLM', 'temperature', fallback=0.3)
                top_p = self.config.getfloat('VLLM', 'top_p', fallback=0.9)
                
                # 发送请求到vLLM API
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                
                caption = response.choices[0].message.content.strip()
                
                # 添加到预设列表
                # 使用第一帧作为缩略图
                thumbnail_frame = self.processed_frames[self.start_frame].copy()
                self.caption_presets.append({
                    "caption": caption,
                    "image": thumbnail_frame
                })
                
                # 创建新的预设项显示
                self.create_preset_item(len(self.caption_presets) - 1, caption, thumbnail_frame)
                
                messagebox.showinfo("成功", f"AI已生成标签并添加到预设列表:\n\n{caption}")
            else:
                messagebox.showerror("错误", "无法获取选中的视频片段")
                
        except Exception as e:
            messagebox.showerror("错误", f"AI标签生成失败: {str(e)}")
        finally:
            loading_window.destroy()

    def create_preset_item(self, index, caption, frame_image):
        """创建预设项显示"""
        # 创建预设项框架
        preset_item = tk.Frame(self.preset_scrollable_frame, bg="#f0f0f0", relief="raised", bd=1)
        preset_item.pack(fill=tk.X, padx=5, pady=5)
        
        # 缩略图框架
        thumbnail_frame = tk.Frame(preset_item, bg="#f0f0f0")
        thumbnail_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 创建缩略图
        thumbnail_image = Image.fromarray(frame_image)
        thumbnail_image = thumbnail_image.resize((60, 40), Image.LANCZOS)
        thumbnail_photo = ImageTk.PhotoImage(thumbnail_image)
        
        # 缩略图标签
        thumbnail_label = tk.Label(thumbnail_frame, image=thumbnail_photo, bg="#f0f0f0")
        thumbnail_label.image = thumbnail_photo  # 保持引用
        thumbnail_label.pack()
        
        # 标签内容框架
        content_frame = tk.Frame(preset_item, bg="#f0f0f0")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标签内容文本
        content_text = tk.Text(content_frame, wrap=tk.WORD, height=4, width=40, font=("Arial", 8))
        content_text.insert(tk.END, caption)
        content_text.config(state=tk.DISABLED)
        content_text.pack(fill=tk.BOTH, expand=True)
        
        # 绑定点击事件
        def on_click(event=None):
            # 显示完整图像和标签
            self.show_full_image(frame_image, caption, index)
        
        preset_item.bind("<Button-1>", on_click)
        thumbnail_label.bind("<Button-1>", on_click)
        content_text.bind("<Button-1>", on_click)
        
        # 为所有子组件绑定点击事件
        for child in preset_item.winfo_children():
            child.bind("<Button-1>", on_click)
            for subchild in child.winfo_children():
                subchild.bind("<Button-1>", on_click)
        
        # 绑定右键菜单事件
        preset_item.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "ai", index))
        thumbnail_label.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "ai", index))
        content_text.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "ai", index))
        
    def show_full_image(self, frame_image, caption, index):
        """显示完整的图像和标签"""
        # 创建新窗口显示完整图像
        image_window = tk.Toplevel(self.root)
        image_window.title("预设详情")
        image_window.geometry("900x1280")  # 增大默认窗口尺寸
        image_window.transient(self.root)
        
        # 将窗口居中
        image_window.update_idletasks()
        x = (image_window.winfo_screenwidth() // 2) - (900 // 2)
        y = (image_window.winfo_screenheight() // 2) - (700 // 2)
        image_window.geometry(f"900x700+{x}+{y}")
        
        # 图像显示
        image_frame = tk.Frame(image_window)
        image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 调整图像大小以适应显示区域
        image_obj = Image.fromarray(frame_image)
        image_obj.thumbnail((880, 400), Image.LANCZOS)
        photo = ImageTk.PhotoImage(image_obj)
        
        image_label = tk.Label(image_frame, image=photo)
        image_label.image = photo  # 保持引用
        image_label.pack()
        
        # 标签内容显示
        caption_frame = tk.Frame(image_window, height=100)  # 设置最大高度 300
        caption_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        caption_frame.pack_propagate(False)  # 阻止 Frame 自动调整大小

        tk.Label(caption_frame, text="标签内容:", font=self.font).pack(anchor=tk.W)
        
        # 创建带滚动条的文本框框架
        text_frame = tk.Frame(caption_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        caption_text = tk.Text(text_frame, wrap=tk.WORD, font=self.font)
        caption_text.insert(tk.END, caption)
        caption_text.config(state=tk.DISABLED)
        
        # 添加滚动条并与文本框关联
        scrollbar = tk.Scrollbar(text_frame, command=caption_text.yview)
        caption_text.config(yscrollcommand=scrollbar.set)
        
        # 使用grid布局管理文本框和滚动条
        caption_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 配置网格权重
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # 按钮框架
        button_frame = tk.Frame(image_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 使用预设按钮
        def use_preset():
            self.tag_entry.delete("1.0", tk.END)
            self.tag_entry.insert("1.0", caption)
            image_window.destroy()
            
        tk.Button(button_frame, text="使用预设", command=use_preset, font=self.font).pack(side=tk.LEFT, padx=5)
        
        # 删除预设按钮
        def delete_preset():
            if messagebox.askyesno("确认", "确定要删除这个标签预设吗？", parent=image_window):
                # 从数据中删除
                del self.caption_presets[index]
                
                # 重新创建所有预设项显示
                for widget in self.preset_scrollable_frame.winfo_children():
                    widget.destroy()
                
                # 修复：只重建AI预设项，不影响手动预设
                for i, preset in enumerate(self.manual_presets):
                    self.create_manual_preset_item(i, preset)
                    
                for i, preset in enumerate(self.caption_presets):
                    self.create_preset_item(i, preset["caption"], preset["image"])
                
                image_window.destroy()
                
        tk.Button(button_frame, text="删除预设", command=delete_preset, font=self.font).pack(side=tk.LEFT, padx=5)
        
        # 关闭按钮
        tk.Button(button_frame, text="关闭", command=image_window.destroy, font=self.font).pack(side=tk.RIGHT, padx=5)
        
    def use_caption_preset(self):
        """使用选中的标签预设填充标签输入框"""
        
    def delete_caption_preset(self):
        """清空所有标签预设"""
        if messagebox.askyesno("确认", "确定要删除所有标签预设吗？"):
            # 清空显示区域
            for widget in self.preset_scrollable_frame.winfo_children():
                widget.destroy()
            
            # 清空数据
            self.caption_presets.clear()
            
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
        
        # 让输入框失去焦点，以便键盘快捷键可以正常使用
        self.root.focus_set()
        
        # 保存当前的结束帧位置
        end_position = self.end_frame
        
        # 清空已选中的开始和结束点
        self.start_frame = 0
        self.end_frame = 0
        
        # 更新标记可视化
        self.draw_tag_markers()
        
        # 将滑块移动到之前设置的结束帧位置
        self.current_frame = end_position
        self.progress.set(self.current_frame)
        self.show_frame()

    def exclude_segment(self):
        """标记当前选中的片段为排除片段"""
        if self.start_frame == 0 and self.end_frame == 0:
            messagebox.showerror("错误", "请先设置开始帧和结束帧")
            return
            
        if self.start_frame > self.end_frame:
            messagebox.showerror("错误", "开始帧不能大于结束帧")
            return
            
        # 添加到排除片段列表
        segment_info = {
            "start": self.start_frame,
            "end": self.end_frame
        }
        self.excluded_segments.append(segment_info)
        
        # 清空已选中的开始和结束点
        self.start_frame = 0
        self.end_frame = 0
        
        # 更新标记可视化
        self.draw_tag_markers()
        
        messagebox.showinfo("成功", "已将选中片段标记为排除片段")
        
    def set_start_frame(self):
        self.start_frame = self.current_frame
        
        # 自动设置结束帧为开始帧之后5秒的位置
        if self.fps > 0:
            # 从配置文件读取分段时长
            segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
            frames_5_seconds = int(segment_duration * self.fps)
            self.end_frame = min(self.current_frame + frames_5_seconds, self.total_frames - 1)
        else:
            # 如果无法获取FPS，则设置为开始帧后100帧
            self.end_frame = min(self.current_frame + 100, self.total_frames - 1)
            
        self.draw_tag_markers()  # 更新标记可视化

    def auto_segment_and_recognize(self):
        """自动按5秒分段并使用AI识别生成标签"""
        # 显示选择调用方式的窗口
        method_window = tk.Toplevel(self.root)
        method_window.title("选择AI调用方式")
        method_window.geometry("300x150")
        method_window.transient(self.root)
        method_window.grab_set()
        
        # 居中显示
        method_window.update_idletasks()
        x = (method_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (method_window.winfo_screenheight() // 2) - (150 // 2)
        method_window.geometry(f"300x150+{x}+{y}")
        
        tk.Label(method_window, text="请选择AI调用方式:", font=self.font).pack(pady=10)
        
        method_var = tk.StringVar(value="local")
        
        tk.Radiobutton(method_window, text="本地模型", variable=method_var, value="local", font=self.font).pack(anchor=tk.W, padx=30)
        tk.Radiobutton(method_window, text="vLLM API", variable=method_var, value="vllm", font=self.font).pack(anchor=tk.W, padx=30)
        
        def confirm_method():
            method = method_var.get()
            method_window.destroy()
            if method == "local":
                self._auto_segment_and_recognize_local()
            else:
                self._auto_segment_and_recognize_vllm()
        
        tk.Button(method_window, text="确定", command=confirm_method, font=self.font).pack(pady=10)
        
    def _auto_segment_and_recognize_local(self):
        """使用本地模型自动按5秒分段并使用AI识别生成标签"""
        if not self.model_loaded:
            # 如果模型未加载，则自动加载模型
            try:
                # 检查是否安装了必要的库
                import torch
                from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
            except ImportError as e:
                messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 transformers 和 torch 库")
                return
            
            # 显示加载提示
            loading_window = tk.Toplevel(self.root)
            loading_window.title("AI处理中")
            loading_window.geometry("300x100")
            loading_window.transient(self.root)
            loading_window.grab_set()
            
            # 将窗口居中显示
            loading_window.update_idletasks()
            x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
            y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
            loading_window.geometry(f"300x100+{x}+{y}")
            
            tk.Label(loading_window, text="正在加载模型...", font=self.font).pack(pady=20)
            self.root.update()
            
            try:
                # 从配置文件读取模型路径
                model_path = self.config.get('MODEL', 'qwen_vl_model_path', fallback=r"J:\models\LLM\Qwen-VL\Qwen3-VL-4B-Instruct")
                
                if not os.path.exists(model_path):
                    messagebox.showerror("错误", f"模型路径不存在: {model_path}\n请确认模型已下载并放置在正确位置")
                    loading_window.destroy()
                    return
                
                # 从配置文件读取模型精度设置
                torch_dtype_str = self.config.get('MODEL', 'torch_dtype', fallback='fp32')
                if torch_dtype_str == 'fp16':
                    torch_dtype = torch.float16
                elif torch_dtype_str == 'bf16':
                    torch_dtype = torch.bfloat16
                else:
                    torch_dtype = torch.float32
                
                # 加载模型
                self.model = AutoModelForVision2Seq.from_pretrained(
                    model_path,
                    device_map="auto",
                    trust_remote_code=True,
                    torch_dtype=torch_dtype
                ).eval()
                self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
                self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
                self.model_loaded = True
                
                loading_window.destroy()
                
            except Exception as e:
                messagebox.showerror("错误", f"模型加载失败: {str(e)}")
                loading_window.destroy()
                return
        
        if self.total_frames <= 0 or self.fps <= 0:
            messagebox.showerror("错误", "无效的视频信息")
            return
            
        # 从配置文件读取分段时长
        segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
        frames_per_segment = int(segment_duration * self.fps)
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("自动分段识别中")
        progress_window.geometry("400x200")  # 增加窗口高度以容纳更多信息
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # 居中显示
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (200 // 2)
        progress_window.geometry(f"400x200+{x}+{y}")
        
        tk.Label(progress_window, text="正在自动分段并识别，请稍候...", font=self.font).pack(pady=10)
        
        # 创建进度条
        progress_bar = ttk.Progressbar(progress_window, mode='determinate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        
        # 添加进度信息标签
        progress_info_label = tk.Label(progress_window, text="0/0 已完成", font=self.font)
        progress_info_label.pack()
        
        progress_percent = tk.Label(progress_window, text="0%", font=self.font)
        progress_percent.pack()
        
        # 添加时间信息标签
        time_info_label = tk.Label(progress_window, text="平均时间: 0s | 剩余时间: 0s", font=self.font)
        time_info_label.pack()
        
        # 计算需要处理的片段数量
        segments = []
        current_frame = 0
        while current_frame < self.total_frames:
            segment_end = min(current_frame + frames_per_segment - 1, self.total_frames - 1)
            
            # 检查这个片段是否在排除列表中
            excluded = False
            for excluded_segment in self.excluded_segments:
                if not (segment_end < excluded_segment["start"] or current_frame > excluded_segment["end"]):
                    excluded = True
                    break
            
            if not excluded:
                segments.append({
                    "start": current_frame,
                    "end": segment_end
                })
                
            current_frame += frames_per_segment
        
        progress_bar['maximum'] = len(segments)
        progress_info_label.config(text=f"0/{len(segments)} 已完成")
        
        # 在新线程中处理AI识别
        def process_segments():
            try:
                # 重新导入必要的库，解决变量作用域问题
                import torch
                from transformers import AutoModelForVision2Seq, AutoProcessor, AutoTokenizer
                import numpy as np
                import time
                
                # 存储需要重新处理的片段
                retry_segments = []
                
                # 初始化时间统计
                start_time = time.time()
                completed_count = 0
                
                # 从配置文件读取生成参数
                max_new_tokens = self.config.getint('MODEL', 'max_new_tokens', fallback=1024)
                temperature = self.config.getfloat('MODEL', 'temperature', fallback=0.6)
                top_p = self.config.getfloat('MODEL', 'top_p', fallback=0.9)
                retry_max_new_tokens = self.config.getint('MODEL', 'retry_max_new_tokens', fallback=512)
                
                for i, segment in enumerate(segments):
                    segment_start_time = time.time()
                    
                    # 提取片段帧
                    frames = []
                    # 从配置文件读取采样帧数
                    max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
                    
                    # 采样最多max_sample_frames帧以提高性能
                    total_frames = segment["end"] - segment["start"] + 1
                    sample_count = min(max_sample_frames, total_frames)
                    
                    if total_frames <= sample_count:
                        indices = list(range(segment["start"], segment["end"] + 1))
                    else:
                        indices = np.linspace(segment["start"], segment["end"], sample_count, dtype=int)
                    
                    for idx in indices:
                        if idx < len(self.processed_frames):
                            # 转换为PIL Image
                            frame_rgb = self.processed_frames[idx]
                            pil_frame = Image.fromarray(frame_rgb)
                            frames.append(pil_frame)
                    
                    # 如果只有一帧，复制以满足视频处理要求
                    if len(frames) == 1:
                        frames.append(frames[0])
                    
                    # 获取用户自定义的提示词
                    user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                    if not user_prompt:
                        user_prompt = "详细描述视频画面"
                    
                    # 构建对话
                    conversation = [{
                        "role": "user",
                        "content": [
                            {"type": "video", "video": frames},
                            {"type": "text", "text": user_prompt}
                        ]
                    }]
                    
                    # 应用模板
                    text_prompt = self.processor.apply_chat_template(
                        conversation,
                        tokenize=False,
                        add_generation_prompt=True
                    )
                    
                    # 处理输入
                    inputs = self.processor(
                        text=text_prompt,
                        videos=[frames],
                        return_tensors="pt"
                    )
                    
                    # 移动到设备
                    inputs = {k: v.to(self.model.device) for k, v in inputs.items()}
                    
                    # 生成输出
                    with torch.no_grad():
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=max_new_tokens,
                            do_sample=True,
                            temperature=temperature,
                            top_p=top_p
                        )
                    
                    # 解码输出
                    input_ids_len = inputs["input_ids"].shape[1]
                    caption = self.tokenizer.decode(
                        outputs[0, input_ids_len:],
                        skip_special_tokens=True
                    )
                    caption = caption.strip()
                    
                    # 检查生成的提示词是否超过300字符，如果超过则需要重新生成
                    if len(caption) > 300:
                        retry_segments.append((i, segment, frames, user_prompt))
                    
                    # 添加到标记列表，不弹窗
                    tag_info = {
                        "start": segment["start"],
                        "end": segment["end"],
                        "tag": caption
                    }
                    self.tags.append(tag_info)
                    self.tag_listbox.insert(tk.END, f"帧 {segment['start']}-{segment['end']}: {caption}")
                    
                    # 更新UI
                    self.root.update()
                    
                    # 更新进度和时间信息
                    completed_count = i + 1
                    segment_end_time = time.time()
                    segment_duration = segment_end_time - segment_start_time
                    elapsed_time = segment_end_time - start_time
                    avg_time_per_segment = elapsed_time / completed_count
                    remaining_segments = len(segments) - completed_count
                    estimated_remaining_time = avg_time_per_segment * remaining_segments
                    
                    # 更新进度（移到处理完成后）
                    progress_bar['value'] = completed_count
                    progress_info_label.config(text=f"{completed_count}/{len(segments)} 已完成")
                    progress_percent.config(text=f"{int((completed_count / len(segments)) * 100)}%")
                    time_info_label.config(text=f"平均时间: {avg_time_per_segment:.2f}s | 剩余时间: {estimated_remaining_time:.2f}s")
                    progress_window.update()
                
                # 处理需要重新生成的片段
                if retry_segments:
                    retry_window = tk.Toplevel(self.root)
                    retry_window.title("重新生成被判断过长的提示词")
                    retry_window.geometry("400x150")
                    retry_window.transient(self.root)
                    retry_window.grab_set()
                    
                    # 居中显示
                    retry_window.update_idletasks()
                    x = (retry_window.winfo_screenwidth() // 2) - (400 // 2)
                    y = (retry_window.winfo_screenheight() // 2) - (150 // 2)
                    retry_window.geometry(f"400x150+{x}+{y}")
                    
                    tk.Label(retry_window, text="正在重新生成长提示词，请稍候...", font=self.font).pack(pady=10)
                    
                    # 创建进度条
                    retry_progress_bar = ttk.Progressbar(retry_window, mode='determinate')
                    retry_progress_bar.pack(pady=10, padx=20, fill=tk.X)
                    retry_progress_bar['maximum'] = len(retry_segments)
                    
                    retry_progress_label = tk.Label(retry_window, text="0%", font=self.font)
                    retry_progress_label.pack()
                    
                    for i, (original_index, segment, frames, user_prompt) in enumerate(retry_segments):
                        # 使用更具体的提示词重新生成
                        retry_prompt = user_prompt + " 请用简洁明了的语言描述，不超过300字。"
                        
                        # 构建对话
                        retry_conversation = [{
                            "role": "user",
                            "content": [
                                {"type": "video", "video": frames},
                                {"type": "text", "text": retry_prompt}
                            ]
                        }]
                        
                        # 应用模板
                        retry_text_prompt = self.processor.apply_chat_template(
                            retry_conversation,
                            tokenize=False,
                            add_generation_prompt=True
                        )
                        
                        # 处理输入
                        retry_inputs = self.processor(
                            text=retry_text_prompt,
                            videos=[frames],
                            return_tensors="pt"
                        )
                        
                        # 移动到设备
                        retry_inputs = {k: v.to(self.model.device) for k, v in retry_inputs.items()}
                        
                        # 生成输出
                        with torch.no_grad():
                            retry_outputs = self.model.generate(
                                **retry_inputs,
                                max_new_tokens=retry_max_new_tokens,  # 减少最大token数以控制长度
                                do_sample=True,
                                temperature=temperature,
                                top_p=top_p
                            )
                        
                        # 解码输出
                        retry_input_ids_len = retry_inputs["input_ids"].shape[1]
                        retry_caption = self.tokenizer.decode(
                            retry_outputs[0, retry_input_ids_len:],
                            skip_special_tokens=True
                        )
                        retry_caption = retry_caption.strip()
                        
                        # 更新标记列表中的内容
                        tag_index = original_index  # 原始索引保持不变
                        if tag_index < len(self.tags):
                            self.tags[tag_index]["tag"] = retry_caption
                            # 更新列表框显示
                            self.tag_listbox.delete(tag_index)
                            self.tag_listbox.insert(tag_index, f"帧 {segment['start']}-{segment['end']}: {retry_caption}")
                        
                        # 更新进度
                        retry_progress_bar['value'] = i + 1
                        retry_progress_percent = int((i + 1) / len(retry_segments) * 100)
                        retry_progress_label.config(text=f"{retry_progress_percent}%")
                        retry_window.update()
                    
                    retry_window.destroy()
                
                # 启用导出按钮
                if len(self.tags) > 0:
                    self.export_btn.config(state=tk.NORMAL)
                    self.save_record_btn.config(state=tk.NORMAL)
                
                # 更新标记可视化
                self.draw_tag_markers()
                
                # 完成后关闭进度窗口并提示
                progress_window.destroy()
                self.root.after(100, lambda: messagebox.showinfo("完成", f"已完成自动分段识别，共生成{len(segments)}个标签"))
                
            except Exception as e:
                progress_window.destroy()
                # 修复变量作用域问题
                error_msg = str(e)
                self.root.after(100, lambda: messagebox.showerror("错误", f"自动分段识别失败: {error_msg}"))
        
        # 启动处理线程
        threading.Thread(target=process_segments, daemon=True).start()
        
    def _generate_ai_caption_vllm(self):
        """使用vLLM API生成标签"""
        try:
            from openai import OpenAI
        except ImportError as e:
            messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 openai 库")
            return
            
        # 显示加载提示
        loading_window = tk.Toplevel(self.root)
        loading_window.title("AI处理中")
        loading_window.geometry("300x150")
        loading_window.transient(self.root)
        loading_window.grab_set()
        
        # 将窗口居中显示
        loading_window.update_idletasks()
        x = (loading_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (loading_window.winfo_screenheight() // 2) - (100 // 2)
        loading_window.geometry(f"300x100+{x}+{y}")
        
        tk.Label(loading_window, text="正在通过vLLM API生成标签...", font=self.font).pack(pady=20)
        self.root.update()
        
        try:
            # 从配置文件读取API设置
            api_base_url = self.config.get('VLLM', 'api_base_url', fallback="http://127.0.0.1:8000/v1")
            api_key = self.config.get('VLLM', 'api_key', fallback="EMPTY")
            model_name = self.config.get('VLLM', 'model_name', fallback="/models/Qwen3-VL-8B-Instruct")
            
            # 配置客户端
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            # 获取选中的视频片段帧
            if self.start_frame < len(self.processed_frames) and self.end_frame < len(self.processed_frames):
                # 从处理后的帧中提取视频片段
                frames = []
                # 从配置文件读取采样帧数
                max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
                
                # 采样最多max_sample_frames帧以提高性能
                total_frames = self.end_frame - self.start_frame + 1
                sample_count = min(max_sample_frames, total_frames)
                
                if total_frames <= sample_count:
                    indices = list(range(self.start_frame, self.end_frame + 1))
                else:
                    indices = np.linspace(self.start_frame, self.end_frame, sample_count, dtype=int)
                
                # 转换帧为base64格式
                frame_data_urls = []
                for i in indices:
                    if i < len(self.processed_frames):
                        # 转为 JPEG 并编码为 base64
                        frame_bgr = cv2.cvtColor(self.processed_frames[i], cv2.COLOR_RGB2BGR)
                        _, buffer = cv2.imencode(".jpg", frame_bgr)
                        encoded = base64.b64encode(buffer).decode("utf-8")
                        data_url = f"data:image/jpeg;base64,{encoded}"
                        frame_data_urls.append(data_url)
                
                # 如果只有一帧，复制以满足视频处理要求
                if len(frame_data_urls) == 1:
                    frame_data_urls.append(frame_data_urls[0])
                
                # 获取用户自定义的提示词
                user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                if not user_prompt:
                    user_prompt = "详细描述视频画面"
                
                # 构造消息：文本 + 多张图片
                content_list = [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
                
                # 添加所有帧
                for url in frame_data_urls:
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": url}
                    })
                
                messages = [{"role": "user", "content": content_list}]
                
                # 从配置文件读取生成参数
                max_tokens = self.config.getint('VLLM', 'max_tokens', fallback=1024)
                temperature = self.config.getfloat('VLLM', 'temperature', fallback=0.3)
                top_p = self.config.getfloat('VLLM', 'top_p', fallback=0.9)
                
                # 发送请求到vLLM API
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                )
                
                caption = response.choices[0].message.content.strip()
                
                # 添加到预设列表
                # 使用第一帧作为缩略图
                thumbnail_frame = self.processed_frames[self.start_frame].copy()
                self.caption_presets.append({
                    "caption": caption,
                    "image": thumbnail_frame
                })
                
                # 创建新的预设项显示
                self.create_preset_item(len(self.caption_presets) - 1, caption, thumbnail_frame)
                
                messagebox.showinfo("成功", f"AI已生成标签并添加到预设列表:\n\n{caption}")
            else:
                messagebox.showerror("错误", "无法获取选中的视频片段")
                
        except Exception as e:
            messagebox.showerror("错误", f"AI标签生成失败: {str(e)}")
        finally:
            loading_window.destroy()

    def _auto_segment_and_recognize_vllm(self):
        """使用vLLM API自动按5秒分段并使用AI识别生成标签"""
        try:
            from openai import OpenAI
        except ImportError as e:
            messagebox.showerror("错误", f"缺少必要的依赖库: {str(e)}\n请安装 openai 库")
            return
            
        if self.total_frames <= 0 or self.fps <= 0:
            messagebox.showerror("错误", "无效的视频信息")
            return
            
        # 从配置文件读取分段时长
        segment_duration = self.config.getint('PROCESSING', 'segment_duration', fallback=5)
        frames_per_segment = int(segment_duration * self.fps)
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("自动分段识别中")
        progress_window.geometry("400x200")  # 增加窗口高度以容纳更多信息
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # 居中显示
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (200 // 2)
        progress_window.geometry(f"400x200+{x}+{y}")
        
        tk.Label(progress_window, text="正在自动分段并识别，请稍候...", font=self.font).pack(pady=10)
        
        # 创建进度条
        progress_bar = ttk.Progressbar(progress_window, mode='determinate')
        progress_bar.pack(pady=10, padx=20, fill=tk.X)
        
        # 添加进度信息标签
        progress_info_label = tk.Label(progress_window, text="0/0 已完成", font=self.font)
        progress_info_label.pack()
        
        progress_percent = tk.Label(progress_window, text="0%", font=self.font)
        progress_percent.pack()
        
        # 添加时间信息标签
        time_info_label = tk.Label(progress_window, text="平均时间: 0s | 剩余时间: 0s", font=self.font)
        time_info_label.pack()
        
        # 计算需要处理的片段数量
        segments = []
        current_frame = 0
        while current_frame < self.total_frames:
            segment_end = min(current_frame + frames_per_segment - 1, self.total_frames - 1)
            
            # 检查这个片段是否在排除列表中
            excluded = False
            for excluded_segment in self.excluded_segments:
                if not (segment_end < excluded_segment["start"] or current_frame > excluded_segment["end"]):
                    excluded = True
                    break
            
            if not excluded:
                segments.append({
                    "start": current_frame,
                    "end": segment_end
                })
                
            current_frame += frames_per_segment
        
        progress_bar['maximum'] = len(segments)
        progress_info_label.config(text=f"0/{len(segments)} 已完成")
        
        # 在新线程中处理AI识别
        def process_segments():
            try:
                # 从配置文件读取API设置
                api_base_url = self.config.get('VLLM', 'api_base_url', fallback="http://127.0.0.1:8000/v1")
                api_key = self.config.get('VLLM', 'api_key', fallback="EMPTY")
                model_name = self.config.get('VLLM', 'model_name', fallback="/models/Qwen3-VL-8B-Instruct")
                
                # 配置客户端
                client = OpenAI(
                    api_key=api_key,
                    base_url=api_base_url,
                    timeout=3600
                )
                
                # 初始化时间统计
                start_time = time.time()
                completed_count = 0
                
                # 从配置文件读取生成参数
                max_tokens = self.config.getint('VLLM', 'max_tokens', fallback=1024)
                temperature = self.config.getfloat('VLLM', 'temperature', fallback=0.3)
                top_p = self.config.getfloat('VLLM', 'top_p', fallback=0.9)
                
                for i, segment in enumerate(segments):
                    segment_start_time = time.time()
                    
                    # 提取片段帧
                    frames = []
                    # 从配置文件读取采样帧数
                    max_sample_frames = self.config.getint('PROCESSING', 'max_sample_frames', fallback=64)
                    
                    # 采样最多max_sample_frames帧以提高性能
                    total_frames = segment["end"] - segment["start"] + 1
                    sample_count = min(max_sample_frames, total_frames)
                    
                    if total_frames <= sample_count:
                        indices = list(range(segment["start"], segment["end"] + 1))
                    else:
                        indices = np.linspace(segment["start"], segment["end"], sample_count, dtype=int)
                    
                    # 转换帧为base64格式
                    frame_data_urls = []
                    for idx in indices:
                        if idx < len(self.processed_frames):
                            # 转为 JPEG 并编码为 base64
                            frame_bgr = cv2.cvtColor(self.processed_frames[idx], cv2.COLOR_RGB2BGR)
                            _, buffer = cv2.imencode(".jpg", frame_bgr)
                            encoded = base64.b64encode(buffer).decode("utf-8")
                            data_url = f"data:image/jpeg;base64,{encoded}"
                            frame_data_urls.append(data_url)
                    
                    # 如果只有一帧，复制以满足视频处理要求
                    if len(frame_data_urls) == 1:
                        frame_data_urls.append(frame_data_urls[0])
                    
                    # 获取用户自定义的提示词
                    user_prompt = self.ai_prompt_entry.get("1.0", tk.END).strip()
                    if not user_prompt:
                        user_prompt = "详细描述视频画面"
                    
                    # 构造消息：文本 + 多张图片
                    content_list = [
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                    
                    # 添加所有帧
                    for url in frame_data_urls:
                        content_list.append({
                            "type": "image_url",
                            "image_url": {"url": url}
                        })
                    
                    messages = [{"role": "user", "content": content_list}]
                    
                    # 发送请求到vLLM API
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        top_p=top_p,
                    )
                    
                    caption = response.choices[0].message.content.strip()
                    
                    # 添加到标记列表，不弹窗
                    tag_info = {
                        "start": segment["start"],
                        "end": segment["end"],
                        "tag": caption
                    }
                    self.tags.append(tag_info)
                    self.tag_listbox.insert(tk.END, f"帧 {segment['start']}-{segment['end']}: {caption}")
                    
                    # 更新UI
                    self.root.update()
                    
                    # 更新进度和时间信息
                    completed_count = i + 1
                    segment_end_time = time.time()
                    segment_duration = segment_end_time - segment_start_time
                    elapsed_time = segment_end_time - start_time
                    avg_time_per_segment = elapsed_time / completed_count
                    remaining_segments = len(segments) - completed_count
                    estimated_remaining_time = avg_time_per_segment * remaining_segments
                    
                    # 更新进度（移到处理完成后）
                    progress_bar['value'] = completed_count
                    progress_info_label.config(text=f"{completed_count}/{len(segments)} 已完成")
                    progress_percent.config(text=f"{int((completed_count / len(segments)) * 100)}%")
                    time_info_label.config(text=f"平均时间: {avg_time_per_segment:.2f}s | 剩余时间: {estimated_remaining_time:.2f}s")
                    progress_window.update()
                
                # 启用导出按钮
                if len(self.tags) > 0:
                    self.export_btn.config(state=tk.NORMAL)
                    self.save_record_btn.config(state=tk.NORMAL)
                
                # 更新标记可视化
                self.draw_tag_markers()
                
                # 完成后关闭进度窗口并提示
                progress_window.destroy()
                self.root.after(100, lambda: messagebox.showinfo("完成", f"已完成自动分段识别，共生成{len(segments)}个标签"))
                
            except Exception as e:
                progress_window.destroy()
                # 修复变量作用域问题
                error_msg = str(e)
                self.root.after(100, lambda: messagebox.showerror("错误", f"自动分段识别失败: {error_msg}"))
        
        # 启动处理线程
        threading.Thread(target=process_segments, daemon=True).start()
        
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
        self.excluded_segments = []  # 清空排除片段
        self.tag_listbox.delete(0, tk.END)  # 清空列表框
        self.export_btn.config(state=tk.DISABLED)  # 禁用导出按钮
        self.save_record_btn.config(state=tk.DISABLED)  # 禁用保存记录按钮
        self.load_record_btn.config(state=tk.DISABLED)  # 禁用加载记录按钮
        
        # 更新UI状态
        self.progress.config(to=self.total_frames-1, state=tk.NORMAL)
        self.play_btn.config(state=tk.NORMAL)
        self.prev_frame_btn.config(state=tk.NORMAL)
        self.next_frame_btn.config(state=tk.NORMAL)
        self.set_start_btn.config(state=tk.NORMAL)
        self.set_end_btn.config(state=tk.NORMAL)
        self.clear_frames_btn.config(state=tk.NORMAL)  # 确保启用清空按钮
        self.add_tag_btn.config(state=tk.NORMAL)
        self.exclude_segment_btn.config(state=tk.NORMAL)  # 启用排除片段按钮
        self.auto_segment_btn.config(state=tk.NORMAL)  # 启用自动分段按钮
        self.ai_generate_btn.config(state=tk.NORMAL)  # 启用AI生成按钮
        
        # 预处理所有帧
        self.preprocess_frames()
        
    def preprocess_frames(self):
        """预处理所有视频帧并存储为图片"""
        if not self.cap:
            return
            
        # 显示加载提示和进度条
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("加载中")
        self.loading_window.geometry("300x200")
        self.loading_window.transient(self.root)
        self.loading_window.grab_set()  # 模态窗口
        
        # 将窗口居中显示
        self.loading_window.update_idletasks()
        x = (self.loading_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (self.loading_window.winfo_screenheight() // 2) - (100 // 2)
        self.loading_window.geometry(f"300x150+{x}+{y}")
        
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
        
        # 从配置文件读取目标帧率
        target_fps = self.config.getint('PROCESSING', 'target_frame_rate', fallback=24)
        
        # 计算帧采样间隔
        if self.fps > target_fps:
            frame_interval = self.fps / target_fps
            effective_fps = target_fps
        else:
            frame_interval = 1
            effective_fps = self.fps
            
        # 处理每一帧
        processed_frame_count = 0
        i = 0
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            # 检查是否应该保留这一帧
            if i % frame_interval < 1:
                # 转换颜色格式
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # 将视频帧调整为720p以提高性能
                frame = self.resize_to_720p(frame)
                
                # 存储处理后的帧
                self.processed_frames.append(frame)
                processed_frame_count += 1
                
                # 更新进度条
                self.loading_progress['value'] = i + 1
                progress_percent = int((i + 1) / self.total_frames * 100)
                self.loading_label.config(text=f"{progress_percent}%")
                self.loading_window.update()
                
            i += 1
                
        self.frames_loaded = True
        # 更新总帧数和帧率为处理后的值
        self.total_frames = processed_frame_count
        self.fps = effective_fps
        
        # 关闭加载窗口
        self.loading_window.destroy()
        
        # 更新进度条范围以匹配处理后的帧数
        self.progress.config(to=self.total_frames-1)
        
        # 更新导出帧率选项为处理后的帧率
        self.export_fps.set(f"{self.fps:.2f}")
        
        # 启用保存和加载记录按钮
        self.save_record_btn.config(state=tk.NORMAL)
        self.load_record_btn.config(state=tk.NORMAL)
                
        # 显示第一帧
        self.show_frame()
        self.draw_tag_markers()  # 绘制标记可视化
        
        # 尝试自动加载该视频的标记记录
        self.auto_load_tag_records()
        
    def show_frame(self):
        if not self.frames_loaded or not self.processed_frames:
            return
            
        if self.current_frame < len(self.processed_frames):
            frame = self.processed_frames[self.current_frame]
            
            # 转换为PIL Image
            image = Image.fromarray(frame)
            
            # 获取画布尺寸
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            # 如果画布尺寸为1（初始状态），使用默认尺寸
            if canvas_width <= 1:
                canvas_width = 800
            if canvas_height <= 1:
                canvas_height = 600
            
            # 计算缩放比例，确保整个图像都能显示在画布内
            img_width, img_height = image.size
            scale_width = canvas_width / img_width
            scale_height = canvas_height / img_height
            scale = min(scale_width, scale_height)
            
            # 如果图像比画布小，则不放大
            if scale > 1:
                scale = 1
            
            # 计算新尺寸
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # 调整图像大小
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # 转换为PhotoImage
            photo = ImageTk.PhotoImage(resized_image)
            
            # 清除画布并显示新图像
            self.video_canvas.delete("all")
            x = (canvas_width - new_width) // 2
            y = (canvas_height - new_height) // 2
            self.video_canvas.create_image(x, y, anchor=tk.NW, image=photo)
            self.video_canvas.image = photo  # 保持引用
            
            # 更新进度条和帧数显示
            self.progress.set(self.current_frame)
            self.frame_label.config(text=f"帧: {self.current_frame}/{self.total_frames-1}")
            
    def save_tag_records(self):
        """保存标记记录到文件"""
        if not self.video_path or not self.tags:
            messagebox.showerror("错误", "没有视频或标记需要保存")
            return
            
        # 生成记录文件路径（与视频同目录，同名但扩展名为.json）
        record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
        
        # 准备保存的数据
        data = {
            "video_path": self.video_path,
            "video_name": os.path.basename(self.video_path),
            "total_frames": self.total_frames,
            "fps": self.fps,
            "tags": self.tags,
            "excluded_segments": self.excluded_segments
        }
        
        try:
            import json
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("成功", f"标记记录已保存到: {record_file}")
        except Exception as e:
            messagebox.showerror("错误", f"保存标记记录失败: {str(e)}")
            
    def load_tag_records(self):
        """从文件加载标记记录"""
        if not self.video_path:
            messagebox.showerror("错误", "请先加载视频文件")
            return
            
        # 生成记录文件路径
        record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
        
        if not os.path.exists(record_file):
            messagebox.showerror("错误", f"未找到标记记录文件: {record_file}")
            return
            
        try:
            import json
            with open(record_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 验证视频文件是否匹配
            if data.get("video_name") != os.path.basename(self.video_path):
                if not messagebox.askyesno("警告", "记录文件与当前视频不匹配，是否仍要加载？"):
                    return
                    
            # 验证帧数是否匹配
            if data.get("total_frames") != self.total_frames:
                if not messagebox.askyesno("警告", "视频帧数与记录不匹配，是否仍要加载？"):
                    return
            
            # 清空现有标记
            self.tags.clear()
            self.excluded_segments.clear()
            self.tag_listbox.delete(0, tk.END)
            
            # 加载标记
            for tag in data.get("tags", []):
                self.tags.append({
                    "start": tag["start"],
                    "end": tag["end"],
                    "tag": tag["tag"]
                })
                self.tag_listbox.insert(tk.END, f"帧 {tag['start']}-{tag['end']}: {tag['tag']}")
                
            # 加载排除片段
            for segment in data.get("excluded_segments", []):
                self.excluded_segments.append({
                    "start": segment["start"],
                    "end": segment["end"]
                })
            
            # 更新UI状态
            if len(self.tags) > 0:
                self.export_btn.config(state=tk.NORMAL)
                
            # 更新标记可视化
            self.draw_tag_markers()
            
            messagebox.showinfo("成功", f"已加载 {len(self.tags)} 个标记记录")
            
        except Exception as e:
            messagebox.showerror("错误", f"加载标记记录失败: {str(e)}")
            
    def auto_load_tag_records(self):
        """自动加载标记记录（在加载视频后调用）"""
        if not self.video_path:
            return
            
        # 生成记录文件路径
        record_file = os.path.splitext(self.video_path)[0] + "_tags.json"
        
        if os.path.exists(record_file):
            try:
                import json
                with open(record_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 验证视频文件是否匹配
                if data.get("video_name") == os.path.basename(self.video_path):
                    # 自动加载标记
                    for tag in data.get("tags", []):
                        self.tags.append({
                            "start": tag["start"],
                            "end": tag["end"],
                            "tag": tag["tag"]
                        })
                        self.tag_listbox.insert(tk.END, f"帧 {tag['start']}-{tag['end']}: {tag['tag']}")
                    
                    # 更新UI状态
                    if len(self.tags) > 0:
                        self.export_btn.config(state=tk.NORMAL)
                        
                    # 更新标记可视化
                    self.draw_tag_markers()
                    
                    print(f"自动加载了 {len(self.tags)} 个标记记录")
                    
            except Exception as e:
                print(f"自动加载标记记录失败: {str(e)}")
                
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
                
                # 生成安全的文件名，移除或替换非法字符
                safe_tag_text = "".join(c for c in tag_text if c.isalnum() or c in (' ', '-', '_')).rstrip()
                # 限制文件名长度
                safe_tag_text = safe_tag_text[:50] if len(safe_tag_text) > 50 else safe_tag_text
                # 替换空格为下划线
                safe_tag_text = safe_tag_text.replace(" ", "_")
                
                # 如果处理后的标签为空，则使用默认名称
                if not safe_tag_text:
                    safe_tag_text = "untitled"
                
                # 生成文件名
                filename = f"video_{i+1:03d}_{safe_tag_text}"
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
        
    def resize_to_720p(self, frame):
        """
        将帧调整为720p分辨率以提高性能
        """
        # 从配置文件读取目标高度
        target_height = self.config.getint('PROCESSING', 'target_frame_height', fallback=720)
        
        h, w = frame.shape[:2]
        
        # 如果高度已经小于等于target_height，则不调整
        if h <= target_height:
            return frame
            
        # 计算新尺寸保持宽高比
        new_height = target_height
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

    def add_preset_tag(self):
        """添加预设标签"""
        preset_text = self.preset_entry.get().strip()
        if not preset_text:
            return
            
        # 添加到手动预设列表
        self.manual_presets.append(preset_text)
        
        # 使用统一的方法创建预设项显示
        self.create_manual_preset_item(len(self.manual_presets) - 1, preset_text)
        
        # 清空输入框
        self.preset_entry.delete(0, tk.END)

    def create_manual_preset_item(self, index, preset_text):
        """创建手动预设项显示"""
        # 创建预设项框架
        preset_item = tk.Frame(self.preset_scrollable_frame, bg="#f0f0f0", relief="raised", bd=1)
        preset_item.pack(fill=tk.X, padx=5, pady=5)
        
        # 标签内容框架
        content_frame = tk.Frame(preset_item, bg="#f0f0f0")
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 标签内容文本
        content_text = tk.Text(content_frame, wrap=tk.WORD, height=4, width=20, font=("Arial", 8))
        content_text.insert(tk.END, preset_text)
        content_text.config(state=tk.DISABLED)
        content_text.pack(fill=tk.BOTH, expand=True)
        
        # 绑定点击事件，用于使用预设
        def on_click(event=None):
            self.use_preset_tag(preset_text)
        
        preset_item.bind("<Button-1>", on_click)
        content_text.bind("<Button-1>", on_click)
        
        # 为所有子组件绑定点击事件
        for child in preset_item.winfo_children():
            child.bind("<Button-1>", on_click)
            for subchild in child.winfo_children():
                subchild.bind("<Button-1>", on_click)
        
        # 绑定右键菜单事件
        preset_item.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "manual", index))
        content_text.bind("<Button-3>", lambda e: self.show_preset_context_menu(e, preset_item, "manual", index))

    def use_preset_tag(self, preset_text):
        """使用预设标签，将其添加到标签输入框的开头"""
        current_text = self.tag_entry.get("1.0", tk.END).strip()
        if current_text:
            new_text = preset_text + "\n" + current_text
        else:
            new_text = preset_text
            
        self.tag_entry.delete("1.0", tk.END)
        self.tag_entry.insert("1.0", new_text)
        
    def show_preset_context_menu(self, event, widget, preset_type, index):
        """显示预设标签的右键菜单"""
        # 保存当前选中的控件引用和类型信息
        self.selected_preset_widget = widget
        self.selected_preset_type = preset_type
        self.selected_preset_index = index
        self.preset_context_menu.post(event.x_root, event.y_root)
        
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

    def edit_preset_tag(self):
        """编辑预设标签"""
        if hasattr(self, 'selected_preset_widget') and hasattr(self, 'selected_preset_type'):
            # 获取当前预设文本
            if self.selected_preset_type == "manual":
                current_text = self.manual_presets[self.selected_preset_index]
            else:  # AI生成的预设
                current_text = self.caption_presets[self.selected_preset_index]["caption"]
                
            # 创建编辑窗口
            edit_window = tk.Toplevel(self.root)
            edit_window.title("编辑预设标签")
            edit_window.geometry("300x150")
            edit_window.transient(self.root)
            edit_window.grab_set()
            
            # 居中显示
            edit_window.update_idletasks()
            x = (edit_window.winfo_screenwidth() // 2) - (300 // 2)
            y = (edit_window.winfo_screenheight() // 2) - (150 // 2)
            edit_window.geometry(f"300x150+{x}+{y}")
            
            tk.Label(edit_window, text="预设标签:", font=self.font).pack(pady=(20, 5))
            edit_entry = tk.Entry(edit_window, font=self.font, width=30)
            edit_entry.pack(pady=5, padx=20)
            edit_entry.insert(0, current_text)
            edit_entry.focus()
            
            def save_changes():
                new_text = edit_entry.get().strip()
                if new_text:
                    if self.selected_preset_type == "manual":
                        # 更新手动预设
                        self.manual_presets[self.selected_preset_index] = new_text
                        # 更新显示文本
                        content_frame = self.selected_preset_widget.winfo_children()[0]  # 标签内容框架
                        content_text = content_frame.winfo_children()[0]  # 文本框
                        content_text.config(state=tk.NORMAL)
                        content_text.delete(1.0, tk.END)
                        content_text.insert(tk.END, new_text)
                        content_text.config(state=tk.DISABLED)
                    else:
                        # 更新AI预设
                        self.caption_presets[self.selected_preset_index]["caption"] = new_text
                        # 更新显示文本
                        content_frame = self.selected_preset_widget.winfo_children()[1]  # 标签内容框架
                        content_text = content_frame.winfo_children()[0]  # 文本框
                        content_text.config(state=tk.NORMAL)
                        content_text.delete(1.0, tk.END)
                        content_text.insert(tk.END, new_text)
                        content_text.config(state=tk.DISABLED)
                    edit_window.destroy()
                else:
                    messagebox.showerror("错误", "预设标签不能为空", parent=edit_window)
            
            button_frame = tk.Frame(edit_window)
            button_frame.pack(pady=20)
            
            tk.Button(button_frame, text="保存", command=save_changes, font=self.font).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="取消", command=edit_window.destroy, font=self.font).pack(side=tk.LEFT, padx=5)
            
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

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTagger(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
