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

    from on_root_click import on_root_click

    from is_child_of import is_child_of

    from toggle_play_with_key import toggle_play_with_key
        
    from set_start_frame_key import set_start_frame_key
            
    from set_end_frame_key import set_end_frame_key

    from draw_tag_markers import draw_tag_markers
                
    from on_progress_change import on_progress_change
        
    from highlight_tag_for_current_frame import highlight_tag_for_current_frame
                
    from toggle_play import toggle_play
            
    from play_video import play_video
        
    from prev_frame import prev_frame
            
    from next_frame import next_frame
            
    from set_start_frame import set_start_frame
        
    from set_end_frame import set_end_frame
        
    from clear_frame_marks import clear_frame_marks
        
    from generate_ai_caption import generate_ai_caption
        
    from _generate_ai_caption_local import _generate_ai_caption_local

    from _generate_ai_caption_vllm import _generate_ai_caption_vllm

    from create_preset_item import create_preset_item
        
    from show_full_image import show_full_image
        
    from use_caption_preset import use_caption_preset
        
    from delete_caption_preset import delete_caption_preset
            
    from add_tag import add_tag

    from exclude_segment import exclude_segment
        
    from set_start_frame import set_start_frame

    from auto_segment_and_recognize import auto_segment_and_recognize
        
    from _auto_segment_and_recognize_local import _auto_segment_and_recognize_local
        
    from _generate_ai_caption_vllm import _generate_ai_caption_vllm

    from _auto_segment_and_recognize_vllm import _auto_segment_and_recognize_vllm
        
    from load_video import load_video
        
    from preprocess_frames import preprocess_frames
        
    from show_frame import show_frame
            
    from save_tag_records import save_tag_records
            
    from load_tag_records import load_tag_records
            
    from auto_load_tag_records import auto_load_tag_records
                
    from export_tags import export_tags
        
    from resize_to_720p import resize_to_720p
        
    from on_window_resize import on_window_resize
            
    from show_tag_context_menu import show_tag_context_menu

    from edit_tag import edit_tag
        
    from delete_tag import delete_tag
        
    from increase_font import increase_font
        
    from decrease_font import decrease_font
            
    from update_font import update_font
            
    from update_widget_font import update_widget_font
        
    from on_closing import on_closing

    from add_preset_tag import add_preset_tag

    from create_manual_preset_item import create_manual_preset_item

    from use_preset_tag import use_preset_tag
        
    from show_preset_context_menu import show_preset_context_menu
        
    from apply_preset_to_all_tags import apply_preset_to_all_tags

    from edit_preset_tag import edit_preset_tag
            
    from delete_preset_tag import delete_preset_tag

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTagger(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
