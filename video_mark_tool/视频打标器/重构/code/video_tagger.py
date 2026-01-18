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
        self.config.read(r'video_mark_tool\视频打标器\重构\code\config.ini', encoding='utf-8')
        print(self.config)
        # 设置初始窗口大小
        window_width = self.config.getint('UI', 'window_width', fallback=1200)
        window_height = self.config.getint('UI', 'window_height', fallback=800)
        # 获取屏幕尺寸并计算居中位置
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
        """初始化主界面UI布局"""
        root = self.root
    
        # 设置整体网格权重以支持响应式布局
        for i in range(6):  # 共6行
            root.grid_rowconfigure(i, weight=0 if i != 1 and i != 4 else 1)
        root.grid_columnconfigure(0, weight=1)
    
        # ===================【顶部控制栏】===================
        control_frame = tk.Frame(root)
        control_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        self.load_btn = tk.Button(control_frame, text="加载视频", command=self.load_video, font=self.font)
        self.load_btn.pack(side=tk.LEFT, padx=5)
    
        # ===================【主要内容区（左右可拖拽面板）】===================
        main_paned = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
        main_paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
    
        # --- 左侧：标签预设区域 ---
        self.preset_panel = tk.Frame(main_paned, bg="lightblue")
        main_paned.add(self.preset_panel, weight=1)
    
        preset_header = tk.Frame(self.preset_panel)
        preset_header.pack(fill=tk.X, pady=5)
        tk.Label(preset_header, text="标签预设:", font=self.font).pack(anchor=tk.W, padx=5)
    
        # 滚动画布容器
        preset_canvas_frame = tk.Frame(self.preset_panel)
        preset_canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
        self.preset_canvas = tk.Canvas(preset_canvas_frame)
        scrollbar = tk.Scrollbar(preset_canvas_frame, orient="vertical", command=self.preset_canvas.yview)
        self.preset_scrollable_frame = tk.Frame(self.preset_canvas)
    
        self.preset_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.preset_canvas.configure(scrollregion=self.preset_canvas.bbox("all"))
        )
    
        self.preset_canvas.create_window((0, 0), window=self.preset_scrollable_frame, anchor="nw")
        self.preset_canvas.configure(yscrollcommand=scrollbar.set)
    
        self.preset_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
        # 预设标签右键菜单
        self.preset_context_menu = tk.Menu(root, tearoff=0, font=self.font)
        self.preset_context_menu.add_command(label="编辑预设", command=self.edit_preset_tag)
        self.preset_context_menu.add_command(label="删除预设", command=self.delete_preset_tag)
        self.preset_context_menu.add_command(label="应用到所有标记", command=self.apply_preset_to_all_tags)
    
        # --- 中间：视频展示区域 ---
        self.video_panel = tk.Frame(main_paned, bg="black")
        main_paned.add(self.video_panel, weight=3)
        self.video_canvas = tk.Canvas(self.video_panel, bg="black")
        self.video_canvas.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    
        # --- 右侧：功能控制面板 ---
        self.control_panel = tk.Frame(main_paned, bg="lightgray")
        main_paned.add(self.control_panel, weight=1)
    
        self.play_btn = tk.Button(self.control_panel, text="播放/暂停", command=self.toggle_play, state=tk.DISABLED, font=self.font)
        self.play_btn.pack(fill=tk.X, padx=5, pady=2)
    
        # 上下帧导航按钮
        frame_nav_frame = tk.Frame(self.control_panel, bg="lightgray")
        frame_nav_frame.pack(fill=tk.X, padx=5, pady=2)
        self.prev_frame_btn = tk.Button(frame_nav_frame, text="上一帧", command=self.prev_frame, state=tk.DISABLED, font=self.font)
        self.prev_frame_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.next_frame_btn = tk.Button(frame_nav_frame, text="下一帧", command=self.next_frame, state=tk.DISABLED, font=self.font)
        self.next_frame_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
    
        # 开始/结束帧设定按钮
        frame_mark_frame = tk.Frame(self.control_panel, bg="lightgray")
        frame_mark_frame.pack(fill=tk.X, padx=5, pady=2)
        self.set_start_btn = tk.Button(frame_mark_frame, text="设置开始帧", command=self.set_start_frame, state=tk.DISABLED, font=self.font)
        self.set_start_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.set_end_btn = tk.Button(frame_mark_frame, text="设置结束帧", command=self.set_end_frame, state=tk.DISABLED, font=self.font)
        self.set_end_btn.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
    
        # 清除帧标记按钮
        self.clear_frames_btn = tk.Button(self.control_panel, text="清空帧标记", command=self.clear_frame_marks, state=tk.DISABLED, font=self.font)
        self.clear_frames_btn.pack(fill=tk.X, padx=5, pady=2)
    
        # AI 相关按钮及输入框
        self.ai_generate_btn = tk.Button(self.control_panel, text="AI生成标签", command=self.generate_ai_caption, state=tk.DISABLED, font=self.font)
        self.ai_generate_btn.pack(fill=tk.X, padx=5, pady=2)
            
        self.delete_preset_btn = tk.Button(self.control_panel, text="删除所有预设", command=self.delete_caption_preset,state=tk.DISABLED, font=self.font)
        self.delete_preset_btn.pack(fill=tk.X, padx=5, pady=2)
    
        ai_prompt_frame = tk.Frame(self.control_panel, bg="lightgray")
        ai_prompt_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(ai_prompt_frame, text="AI提示词:", font=self.font, bg="lightgray").pack(anchor=tk.W)
        self.ai_prompt_entry = tk.Text(ai_prompt_frame, height=3, font=("Arial", 8))
        self.ai_prompt_entry.pack(fill=tk.X, pady=2)
        default_prompt = self.config.get('PROMPTS', 'video_prompt', fallback="详细描述视频画面。")
        self.ai_prompt_entry.insert("1.0", default_prompt)
        self.ai_prompt_entry.config(state=tk.NORMAL, takefocus=True)
    
        # 字体缩放按钮
        font_control_frame = tk.Frame(self.control_panel, bg="lightgray")
        font_control_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(font_control_frame, text="字体大小:", font=self.font, bg="lightgray").pack(side=tk.LEFT)
        self.font_decrease_btn = tk.Button(font_control_frame, text="-", command=self.decrease_font, width=3, font=self.font)
        self.font_decrease_btn.pack(side=tk.LEFT, padx=2)
        self.font_increase_btn = tk.Button(font_control_frame, text="+", command=self.increase_font, width=3, font=self.font)
        self.font_increase_btn.pack(side=tk.LEFT, padx=2)
    
        # 预设按钮区
        preset_btn_frame = tk.Frame(self.preset_panel)
        preset_btn_frame.pack(fill=tk.X, pady=5)
    
        # ===================【进度条区域】===================
        progress_frame = tk.Frame(root)
        progress_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
    
        self.frame_label = tk.Label(progress_frame, text="帧: 0/0", font=self.font)
        self.frame_label.pack()
    
        self.progress_canvas = tk.Canvas(progress_frame, height=30)
        self.progress_canvas.pack(fill=tk.X, pady=2)
    
        self.progress = tk.Scale(progress_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                 command=self.on_progress_change, state=tk.DISABLED, showvalue=0)
        self.progress.pack(fill=tk.X)
    
        # ===================【标签输入与操作区】===================
        tag_frame = tk.Frame(root)
        tag_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
    
        tk.Label(tag_frame, text="标签:", font=self.font).pack(side=tk.LEFT, padx=(5, 2))
    
        # 多行标签输入框 + 滚动条
        self.tag_entry = tk.Text(tag_frame, height=3, font=self.font)
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
    
        scrollbar = tk.Scrollbar(tag_frame, command=self.tag_entry.yview)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tag_entry.config(yscrollcommand=scrollbar.set)
    
        # 功能按钮
        self.add_tag_btn = tk.Button(tag_frame, text="添加标记", command=self.add_tag, state=tk.DISABLED, font=self.font)
        self.add_tag_btn.pack(side=tk.LEFT, padx=2)
    
        self.exclude_segment_btn = tk.Button(tag_frame, text="排除片段", command=self.exclude_segment, state=tk.DISABLED, font=self.font)
        self.exclude_segment_btn.pack(side=tk.LEFT, padx=2)
    
        self.auto_segment_btn = tk.Button(tag_frame, text="自动分段AI识别", command=self.auto_segment_and_recognize, state=tk.DISABLED, font=self.font)
        self.auto_segment_btn.pack(side=tk.LEFT, padx=2)

        # 添加重新生成所有标签的按钮
        self.regenerate_all_tags_btn = tk.Button(tag_frame, text="重新生成所有标签", command=self.regenerate_all_tags, state=tk.DISABLED, font=self.font)
        self.regenerate_all_tags_btn.pack(side=tk.LEFT, padx=2)

        # 预设相关控件
        self.preset_entry = tk.Entry(tag_frame, width=15, font=self.font)
        self.preset_entry.pack(side=tk.LEFT, padx=2)
        self.add_preset_btn = tk.Button(tag_frame, text="添加预设", command=self.add_preset_tag, font=self.font)
        self.add_preset_btn.pack(side=tk.LEFT, padx=2)

        # ===================【标签列表区】===================
        list_frame = tk.Frame(root)
        list_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
    
        tk.Label(list_frame, text="已标记片段:", font=self.font).grid(row=0, column=0, columnspan=2, sticky="w")
    
        self.tag_listbox = tk.Listbox(list_frame, font=self.font)
        self.tag_listbox.grid(row=1, column=0, sticky="nsew")
    
        # 标签列表右键菜单
        self.tag_context_menu = tk.Menu(self.tag_listbox, tearoff=0, font=self.font)
        self.tag_context_menu.add_command(label="编辑标签", command=self.edit_tag)
        self.tag_context_menu.add_command(label="删除标签", command=self.delete_tag)
        self.tag_listbox.bind("<Button-3>", self.show_tag_context_menu)
    
        list_scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tag_listbox.yview)
        list_scrollbar.grid(row=1, column=1, sticky="ns")
        self.tag_listbox.config(yscrollcommand=list_scrollbar.set)
    
        # ===================【导出设置区】===================
        export_frame = tk.Frame(root)
        export_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
    
        tk.Label(export_frame, text="导出帧率:", font=self.font).pack(side=tk.LEFT, padx=(0, 5))
        self.fps_entry = tk.Entry(export_frame, textvariable=self.export_fps, width=10, font=self.font)
        self.fps_entry.pack(side=tk.LEFT, padx=5)
    
        self.export_btn = tk.Button(export_frame, text="导出所有标记片段", command=self.export_tags, state=tk.DISABLED, font=self.font)
        self.export_btn.pack(side=tk.LEFT, padx=5)
    
        self.save_record_btn = tk.Button(export_frame, text="保存标记记录", command=self.save_tag_records, state=tk.DISABLED, font=self.font)
        self.save_record_btn.pack(side=tk.LEFT, padx=5)
    
        self.load_record_btn = tk.Button(export_frame, text="加载标记记录", command=self.load_tag_records, state=tk.DISABLED, font=self.font)
        self.load_record_btn.pack(side=tk.LEFT, padx=5)
    
        # ===================【全局事件绑定】===================
        self.root.bind('<Configure>', self.on_window_resize)
        self.root.bind('<space>', self.toggle_play_with_key)
        self.root.bind('<Key-a>', self.set_start_frame_key)
        self.root.bind('<Key-d>', self.set_end_frame_key)
        self.root.bind('<Button-1>', self.on_root_click)


    from ui_events.on_root_click import on_root_click
    from ui_events.toggle_play_with_key import toggle_play_with_key
    from ui_events.set_start_frame_key import set_start_frame_key
    from ui_events.set_end_frame_key import set_end_frame_key
    from ui_events.on_progress_change import on_progress_change
    from ui_events.toggle_play import toggle_play
    from ui_events.prev_frame import prev_frame
    from ui_events.next_frame import next_frame
    from ui_events.set_start_frame import set_start_frame
    from ui_events.set_end_frame import set_end_frame
    from ui_events.clear_frame_marks import clear_frame_marks
    from ui_events.on_window_resize import on_window_resize
    from ui_events.show_tag_context_menu import show_tag_context_menu
    from ui_events.edit_tag import edit_tag
    from ui_events.delete_tag import delete_tag
    from ui_events.increase_font import increase_font
    from ui_events.decrease_font import decrease_font
    from ui_events.update_font import update_font
    from ui_events.update_widget_font import update_widget_font
    from ui_events.on_closing import on_closing
    from ui_events.show_preset_context_menu import show_preset_context_menu

    # 视频处理
    from video_processing.load_video import load_video
    from video_processing.preprocess_frames import preprocess_frames
    from video_processing.show_frame import show_frame
    from video_processing.play_video import play_video
    from video_processing.resize_to_720p import resize_to_720p

    # 标签管理
    from tag_management.add_tag import add_tag
    from tag_management.exclude_segment import exclude_segment
    from tag_management.save_tag_records import save_tag_records
    from tag_management.load_tag_records import load_tag_records
    from tag_management.auto_load_tag_records import auto_load_tag_records
    from tag_management.export_tags import export_tags
    from tag_management.regenerate_all_tags import regenerate_all_tags, _regenerate_all_tags_thread, _generate_single_tag_caption
    # AI功能
    from ai_features.generate_ai_caption import generate_ai_caption
    from ai_features._generate_ai_caption_local import _generate_ai_caption_local,_generate_ai_caption_local_thread
    from ai_features._generate_ai_caption_vllm import _generate_ai_caption_vllm
    from ai_features.auto_segment_and_recognize import auto_segment_and_recognize
    from ai_features._auto_segment_and_recognize_local import _auto_segment_and_recognize_local
    from ai_features._auto_segment_and_recognize_vllm import _auto_segment_and_recognize_vllm

    # 预设标签
    from presets.create_preset_item import create_preset_item
    from presets.use_caption_preset import use_caption_preset
    from presets.delete_caption_preset import delete_caption_preset
    from presets.add_preset_tag import add_preset_tag
    from presets.create_manual_preset_item import create_manual_preset_item
    from presets.use_preset_tag import use_preset_tag
    from presets.apply_preset_to_all_tags import apply_preset_to_all_tags
    from presets.edit_preset_tag import edit_preset_tag
    from presets.delete_preset_tag import delete_preset_tag
    from presets.show_full_image import show_full_image

    # 工具函数
    from utils.is_child_of import is_child_of
    from utils.draw_tag_markers import draw_tag_markers
    from utils.highlight_tag_for_current_frame import highlight_tag_for_current_frame


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTagger(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()