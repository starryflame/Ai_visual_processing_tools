#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI 视觉处理工具集 - 统一启动器
整合项目中所有带 UI 界面的工具
"""

import sys
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox, font
import subprocess
import threading
import webbrowser

# ============================================================
# 路径常量
# 全部基于本文件所在目录解析，换盘符/换机器都不需要改这里
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# 视频类工具使用的独立虚拟环境
# 本地不存在时 launch_tool 会自动回退到当前解释器，不会报错
VIDEO_VENV = os.path.join(PROJECT_ROOT, "video_mark_tool", ".venv", "Scripts", "python.exe")


# ============================================================
# 工具配置数据
# ============================================================
TOOLS_CONFIG = {
    "打标 / 标签": [
        {
            "name": "图片打标器 (主程序)",
            "path": "tools/tagging/image_tagger/main.py",
            "desc": "缩略图网格浏览、标签增删改查、AI提示词生成、批量打标、导出重命名",
            "icon": "🖼️", "icon_color": "#4A90D9",
            "ui": "gui"
        },
        {
            "name": "视频打标器",
            "path": "tools/tagging/video_tagger/code/video_tagger.py",
            "desc": "视频逐帧标记、AI标签生成、片段裁剪导出、标签预设管理",
            "icon": "🎬", "icon_color": "#5B9ED4",
            "ui": "gui",
            "venv": VIDEO_VENV
        },
        {
            "name": "标签预览管理器",
            "path": "tools/tagging/label_manager/pic_video_label_manager.py",
            "desc": "图片/视频混合浏览、标签编辑、拖拽导入、视频播放、双击快速删除",
            "icon": "📁", "icon_color": "#6DB3D9",
            "ui": "gui"
        },
        {
            "name": "词频统计工具",
            "path": "tools/tagging/word_frequency/词频统计.py",
            "desc": "加载标签数据、词频统计排序、批量替换标签、AI重新生成标签",
            "icon": "📊", "icon_color": "#3D7AB5",
            "ui": "gui"
        },
        {
            "name": "图片视频标签过滤",
            "path": "tools/tagging/label_filter/label_filter_ui.py",
            "desc": "缩略图网格浏览、按标签筛选图片/视频、多选批量导出或删除",
            "icon": "🏷️", "icon_color": "#4488C5",
            "ui": "gui"
        },
        {
            "name": "数据集标签提取",
            "path": "tools/tagging/label_extractor/label_extractor.py",
            "desc": "从数据集目录递归收集所有txt标签文件，汇总合并为单一文本文件",
            "icon": "📋", "icon_color": "#7BA8CC",
            "ui": "cli"
        }
    ],
    "图片处理": [
        {
            "name": "图片缩放工具",
            "path": "tools/image_processing/image_resizer/image_resizer.py",
            "desc": "拖拽导入图片、批量压缩到指定文件大小、质量/分辨率调节、格式转换",
            "icon": "📐", "icon_color": "#43A047",
            "ui": "gui"
        },
        {
            "name": "图片过滤工具",
            "path": "tools/image_processing/image_filter/main.py",
            "desc": "用AI视觉模型按自定义条件筛选图片、双栏YES/NO分类、一键导出",
            "icon": "🔍", "icon_color": "#66BB6A",
            "ui": "gui"
        },
        {
            "name": "图片批量裁剪 (网页版)",
            "path": "tools/image_processing/image_crop/batch_image_crop_offline.html",
            "desc": "浏览器内运行、多比例裁剪预设、拖拽导入、暗色模式、ZIP打包导出",
            "icon": "✂️", "icon_color": "#388E3C",
            "ui": "gui"
        }
    ],
    "视频处理": [
        {
            "name": "视频转图片",
            "path": "tools/video_processing/video_to_image/视频转图片.py",
            "desc": "批量将视频逐帧导出为图片序列、支持webp/mp4等格式、多线程加速",
            "icon": "🎞️", "icon_color": "#EF6C00",
            "ui": "cli",
            "venv": VIDEO_VENV
        },
        {
            "name": "视频拆分工具",
            "path": "tools/video_processing/video_splitter/通用拆分视频.py",
            "desc": "按指定秒数将视频切分为多个片段、保留音频、使用ffmpeg精确切割",
            "icon": "✂️", "icon_color": "#FB8C00",
            "ui": "cli"
        },
        {
            "name": "视频时长扩充",
            "path": "tools/video_processing/video_extender/扩充视频时长.py",
            "desc": "将短视频通过慢放拉伸到目标时长(默认5秒)、固定帧率输出",
            "icon": "⏱️", "icon_color": "#F57C00",
            "ui": "cli"
        },
        {
            "name": "批量修改帧率",
            "path": "tools/video_processing/frame_rate_changer/frame_rate_changer.py",
            "desc": "用ffmpeg批量调整视频FPS(默认30fps)、保留音频流、支持多种格式",
            "icon": "⚡", "icon_color": "#FF9800",
            "ui": "cli"
        }
    ],
    "配对工具": [
        {
            "name": "图片配对工具",
            "path": "tools/pairing/image_pairing/main.py",
            "desc": "双面板图片浏览、AI视觉模型自动配对人物、配对预览拼接图、批量导出",
            "icon": "🔗", "icon_color": "#8E24AA",
            "ui": "gui"
        },
        {
            "name": "相似度配对工具",
            "path": "tools/pairing/similarity_pairing/main.py",
            "desc": "双面板图片浏览、感知哈希+颜色直方图计算相似度、自动匹配最相似图片",
            "icon": "🧩", "icon_color": "#AB47BC",
            "ui": "gui"
        }
    ],
    "格式转换": [
        {
            "name": "全能媒体转换器",
            "path": "tools/media_conversion/media_converter/transform.py",
            "desc": "图片/视频/音频格式互转、视频转GIF(可控帧率分辨率)、批量处理",
            "icon": "🔄", "icon_color": "#00897B",
            "ui": "gui"
        },
        {
            "name": "改音频文件后缀",
            "path": "tools/media_conversion/music_kmg/music_kmg.py",
            "desc": "扫描目录下所有 .kgm.flac 文件，批量重命名为 .kgm 后缀",
            "icon": "🔓", "icon_color": "#26A69A",
            "ui": "cli"
        }
    ],
    "文件处理": [
        {
            "name": "文件夹批处理工具",
            "path": "tools/file_operations/folder_batch/folder_batch.py",
            "desc": "拆分大文件夹(保持图片/标签配对)、扁平化子目录、随机打乱文件名",
            "icon": "📂", "icon_color": "#6D4C41",
            "ui": "gui"
        },
        {
            "name": "批量改文件名",
            "path": "tools/file_operations/batch_rename/batch_rename.py",
            "desc": "批量删除文件名中的特定后缀(_real/_fake/_hd/_sd)，支持扩展后缀列表",
            "icon": "✏️", "icon_color": "#8D6E63",
            "ui": "cli"
        },
        {
            "name": "TXT 逗号分隔转换",
            "path": "tools/file_operations/txt_formatter/txt_formatter.py",
            "desc": "批量将TXT文件中中文逗号(，)替换为英文逗号(,)并删除所有空格",
            "icon": "📝", "icon_color": "#A1887F",
            "ui": "cli"
        }
    ],
    "文档处理": [
        {
            "name": "PDF 转图片工具",
            "path": "tools/document_processing/pdf_to_image/pdf_to_image.py",
            "desc": "单个PDF或批量文件夹扫描、每页转PNG/JPG/WEBP、加密PDF自动弹窗输入密码、DPI可调",
            "icon": "📄", "icon_color": "#607D8B",
            "ui": "gui"
        }
    ],
    "音频工具": [
        {
            "name": "多段音频拼接",
            "path": "tools/audio/audio_merger/audio_merger_gui.py",
            "desc": "多段音频合并拼接、支持按名称/修改时间排序、可选输出格式(mp3/wav/flac等)",
            "icon": "🎵", "icon_color": "#E91E63",
            "ui": "gui"
        },
        {
            "name": "TTS 文字转语音",
            "path": "tools/audio/tts/qwen3tts/gradio的tts.py",
            "desc": "Qwen3TTS语音合成、多音色可选(御姐/萝莉/老男人等)、Gradio客户端调用",
            "icon": "🗣️", "icon_color": "#F06292",
            "ui": "gui"
        }
    ],
    "ComfyUI AI 工具": [
        {
            "name": "批量动漫转写实",
            "path": "tools/comfyui/batch_anime2real.py",
            "desc": "连接ComfyUI批量将动漫图转为写实风格、实时预览、支持多工作流切换",
            "icon": "🎨", "icon_color": "#5C6BC0",
            "ui": "gui"
        },
        {
            "name": "批量动漫转写实 (网页查看器)",
            "path": "tools/comfyui/batch_anime2real_viewer.py",
            "desc": "局域网网页实时查看动漫转写实批处理的原图/生成图对比,平板浏览器直接访问",
            "icon": "🌐", "icon_color": "#7986CB",
            "ui": "gui"
        },
        {
            "name": "批量图片放大",
            "path": "tools/comfyui/batch_image_upscale.py",
            "desc": "连接ComfyUI使用SeedVR2模型批量放大图片、分辨率控制、断点续传",
            "icon": "🔍", "icon_color": "#7986CB",
            "ui": "gui"
        },
        {
            "name": "真人转动漫",
            "path": "tools/comfyui/真人转动漫.py",
            "desc": "连接ComfyUI使用LoRA将真人照片转为动漫风格、实时预览、半自动模式",
            "icon": "👤", "icon_color": "#3F51B5",
            "ui": "gui"
        },
        {
            "name": "Wan22 视频放大",
            "path": "tools/comfyui/wan22放大.py",
            "desc": "连接ComfyUI使用Wan2.2模型对视频进行高清放大处理",
            "icon": "⬆️", "icon_color": "#9FA8DA",
            "ui": "cli"
        },
        {
            "name": "提示词提取",
            "path": "tools/comfyui/提示词提取.py",
            "desc": "从ComfyUI生成的PNG图片或视频文件中提取工作流提示词(节点113文本)",
            "icon": "💬", "icon_color": "#7E57C2",
            "ui": "cli"
        },
        {
            "name": "插帧工具",
            "path": "tools/comfyui/插帧.py",
            "desc": "连接ComfyUI使用VHS节点对视频进行帧间插值、提升流畅度",
            "icon": "🎬", "icon_color": "#B39DDB",
            "ui": "cli"
        }
    ]
}


# ============================================================
# 配色与样式常量
# ============================================================
class Theme:
    """天蓝色主题"""
    # 背景
    BG_ROOT      = "#e8f4fd"     # 最外层浅蓝背景
    BG_MAIN      = "#f0f7fc"     # 主内容区
    BG_HEADER    = "#ffffff"     # 顶部栏
    BG_CARD      = "#ffffff"     # 卡片底色
    BG_CATEGORY  = "#f0f7fc"     # 分类区域背景（同主内容区）

    # 强调色
    ACCENT       = "#2196F3"     # 主蓝色
    ACCENT_DEEP  = "#1565C0"     # 深蓝（hover）
    ACCENT_LIGHT = "#e3f2fd"     # 极浅蓝（卡片顶部色条）
    ACCENT_PALE  = "#bbdefb"     # 浅蓝边框

    # 文字
    TEXT_TITLE   = "#0d2137"     # 标题深色
    TEXT_BODY    = "#37474f"     # 正文
    TEXT_HINT    = "#90a4ae"     # 辅助文字
    TEXT_ONCARD  = "#263238"     # 卡片内标题
    TEXT_WHITE   = "#ffffff"

    # 徽章
    BADGE_GUI_BG = "#e8f5e9"
    BADGE_GUI_FG = "#2e7d32"
    BADGE_CLI_BG = "#fff8e1"
    BADGE_CLI_FG = "#e65100"

    # 边框
    BORDER       = "#dbe8f0"
    SHADOW       = "#b0c4de"     # 模拟阴影


# ============================================================
# UI 主类
# ============================================================
class ToolkitLauncher:
    CARD_W = 280
    CARD_H = 162
    COLUMNS = 3
    CARD_PADX = 14
    CARD_PADY = 10

    def __init__(self, root):
        self.root = root
        self.root.title("AI 视觉处理工具集")
        self.root.geometry("960x720")
        self.root.minsize(740, 500)
        self.root.configure(bg=Theme.BG_ROOT)

        # 收集所有工具展平列表（用于搜索）
        self.all_tools = []
        for cat, tools in TOOLS_CONFIG.items():
            for t in tools:
                t_copy = dict(t)
                t_copy["category"] = cat
                self.all_tools.append(t_copy)

        self._category_frames = {}
        self._category_labels = {}
        self.setup_fonts()
        self.setup_ui()

    # ---- 字体 ----
    def setup_fonts(self):
        self.f_title    = font.Font(family="Microsoft YaHei", size=22, weight="bold")
        self.f_subtitle = font.Font(family="Microsoft YaHei", size=10)
        self.f_cat      = font.Font(family="Microsoft YaHei", size=13, weight="bold")
        self.f_card_name = font.Font(family="Microsoft YaHei", size=11, weight="bold")
        self.f_card_desc = font.Font(family="Microsoft YaHei", size=9)
        self.f_badge    = font.Font(family="Microsoft YaHei", size=8, weight="bold")
        self.f_search   = font.Font(family="Microsoft YaHei", size=11)
        self.f_status   = font.Font(family="Microsoft YaHei", size=9)

    # ---- 整体布局 ----
    def setup_ui(self):
        # ---------- 顶部导航栏 ----------
        header = tk.Frame(self.root, bg=Theme.BG_HEADER, height=72)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)

        # 左侧标题区
        left = tk.Frame(header, bg=Theme.BG_HEADER)
        left.pack(side=tk.LEFT, padx=(28, 0), pady=12)

        tk.Label(
            left, text="🚀", font=("Segoe UI Emoji", 26),
            bg=Theme.BG_HEADER
        ).pack(side=tk.LEFT)

        title_block = tk.Frame(left, bg=Theme.BG_HEADER)
        title_block.pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(
            title_block, text="AI 视觉处理工具集",
            font=self.f_title, bg=Theme.BG_HEADER, fg=Theme.TEXT_TITLE
        ).pack(anchor="w")


        # 右侧搜索栏
        right = tk.Frame(header, bg=Theme.BG_HEADER)
        right.pack(side=tk.RIGHT, padx=28, pady=12)

        search_frame = tk.Frame(right, bg=Theme.BG_HEADER, highlightbackground=Theme.BORDER,
                                highlightthickness=1, padx=2, pady=2)
        search_frame.pack()

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._on_search())
        self.search_entry = tk.Entry(
            search_frame, textvariable=self.search_var,
            font=self.f_search, fg=Theme.TEXT_BODY,
            bg=Theme.BG_MAIN, relief=tk.FLAT,
            width=22, insertbackground=Theme.ACCENT
        )
        self.search_entry.pack(side=tk.LEFT, ipady=6, padx=(10, 0))
        # 占位文字
        self._search_placeholder = "🔍  搜索工具..."
        self.search_entry.insert(0, self._search_placeholder)
        self.search_entry.configure(fg=Theme.TEXT_HINT)
        self.search_entry.bind("<FocusIn>", self._on_search_focus_in)
        self.search_entry.bind("<FocusOut>", self._on_search_focus_out)

        # ---------- 主滚动区 ----------
        self.canvas = tk.Canvas(self.root, bg=Theme.BG_MAIN, highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.inner = tk.Frame(self.canvas, bg=Theme.BG_MAIN)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self._bind_mousewheel()

        # ---------- 底部状态栏 ----------
        footer = tk.Frame(self.root, bg=Theme.BG_HEADER, height=28)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)

        self.status_label = tk.Label(
            footer, text="", font=self.f_status,
            bg=Theme.BG_HEADER, fg=Theme.TEXT_HINT
        )
        self.status_label.pack(side=tk.LEFT, padx=20)
        self._update_status()

        # ---------- 构建全部卡片 ----------
        self._build_all_cards()

    # ---- 搜索 ----
    def _on_search_focus_in(self, _event):
        if self.search_entry.get() == self._search_placeholder:
            self.search_entry.delete(0, tk.END)
            self.search_entry.configure(fg=Theme.TEXT_BODY)

    def _on_search_focus_out(self, event):
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, self._search_placeholder)
            self.search_entry.configure(fg=Theme.TEXT_HINT)

    def _on_search(self):
        """搜索/过滤卡片"""
        if not self._category_frames:  # UI 尚未构建完毕
            return
        keyword = self.search_var.get().strip()
        if keyword == self._search_placeholder:
            keyword = ""
        keyword_lower = keyword.lower()

        found_any = False
        for cat, tools in TOOLS_CONFIG.items():
            frame = self._category_frames.get(cat)
            if not frame:
                continue
            cat_visible = False
            for child in frame.winfo_children():
                if hasattr(child, "_tool_data"):
                    td = child._tool_data
                    match = (not keyword_lower or
                             keyword_lower in td["name"].lower() or
                             keyword_lower in td["desc"].lower() or
                             keyword_lower in cat.lower())
                    if match:
                        child.pack(side=tk.LEFT, padx=self.CARD_PADX // 2, pady=self.CARD_PADY // 2)
                        cat_visible = True
                        found_any = True
                    else:
                        child.pack_forget()
            # 显示/隐藏整个分类
            if cat_visible or not keyword_lower:
                self._show_category(cat)
            else:
                self._hide_category(cat)
            # 分类标题也跟着显隐
            header_label = self._category_labels.get(cat)
            if header_label:
                if cat_visible or not keyword_lower:
                    header_label.pack(anchor="w", padx=8, pady=(20, 6))
                else:
                    header_label.pack_forget()

        self._update_status(keyword_lower and found_any)
        # 滚动到顶部
        self.canvas.yview_moveto(0)

    # ---- 构建卡片 ----
    def _build_all_cards(self):
        # 内边距容器
        pad_frame = tk.Frame(self.inner, bg=Theme.BG_MAIN)
        pad_frame.pack(fill=tk.BOTH, expand=True, padx=24, pady=16)

        for cat, tools in TOOLS_CONFIG.items():
            # 分类标题
            gui_n = sum(1 for t in tools if t.get("ui", "gui") == "gui")
            cli_n = sum(1 for t in tools if t.get("ui", "gui") == "cli")
            parts = [f"{cat}"]
            if gui_n:
                parts.append(f"{gui_n} 个 GUI")
            if cli_n:
                parts.append(f"{cli_n} 个脚本")
            cat_text = "  ·  ".join(parts)

            cat_label = tk.Label(
                pad_frame, text=cat_text,
                font=self.f_cat, bg=Theme.BG_MAIN, fg=Theme.TEXT_TITLE
            )
            cat_label.pack(anchor="w", padx=8, pady=(20, 6))
            self._category_labels[cat] = cat_label

            # 工具卡片容器
            cards_frame = tk.Frame(pad_frame, bg=Theme.BG_MAIN)
            cards_frame.pack(fill=tk.X, pady=(0, 4))
            self._category_frames[cat] = cards_frame

            for tool in tools:
                card = self._create_card(cards_frame, tool)
                card.pack(side=tk.LEFT, padx=self.CARD_PADX // 2, pady=self.CARD_PADY // 2)

    def _show_category(self, cat):
        f = self._category_frames.get(cat)
        if f:
            f.pack(fill=tk.X, pady=(0, 4))
        lbl = self._category_labels.get(cat)
        if lbl:
            lbl.pack(anchor="w", padx=8, pady=(20, 6))

    def _hide_category(self, cat):
        f = self._category_frames.get(cat)
        if f:
            f.pack_forget()
        lbl = self._category_labels.get(cat)
        if lbl:
            lbl.pack_forget()

    def _create_card(self, parent, tool_data):
        """创建单个工具卡片"""
        card = tk.Frame(parent, bg=Theme.BG_CARD, width=self.CARD_W, height=self.CARD_H,
                        highlightbackground=Theme.BORDER, highlightthickness=1)
        card.pack_propagate(False)
        card._tool_data = tool_data

        # --- 左侧色条 ---
        accent_bar = tk.Frame(card, bg=Theme.ACCENT, width=4)
        accent_bar.place(x=0, y=0, relheight=1.0)
        accent_bar._bar = True

        # --- 彩色圆形图标 ---
        icon_color = tool_data.get("icon_color", Theme.ACCENT)
        icon_text = tool_data["icon"]
        icon_canvas = tk.Canvas(card, width=38, height=38,
                                bg=Theme.BG_CARD, highlightthickness=0)
        icon_canvas.place(x=14, y=12)
        # 画彩色圆底
        icon_canvas.create_oval(2, 2, 36, 36, fill=icon_color, outline="", tags="circle")
        # 画 emoji 图标
        icon_canvas.create_text(19, 19, text=icon_text, font=("Segoe UI Emoji", 16),
                                anchor="center", tags="emoji")

        # UI 类型徽章
        ui_type = tool_data.get("ui", "gui")
        if ui_type == "gui":
            badge_text, badge_bg, badge_fg = "GUI", Theme.BADGE_GUI_BG, Theme.BADGE_GUI_FG
        else:
            badge_text, badge_bg, badge_fg = "脚本", Theme.BADGE_CLI_BG, Theme.BADGE_CLI_FG

        badge = tk.Label(card, text=badge_text, font=self.f_badge,
                         bg=badge_bg, fg=badge_fg, padx=8, pady=2)
        badge.place(x=self.CARD_W - 60, y=16)

        # --- 工具名称 ---
        name_label = tk.Label(card, text=tool_data["name"], font=self.f_card_name,
                              bg=Theme.BG_CARD, fg=Theme.TEXT_ONCARD,
                              anchor="nw", wraplength=195)
        name_label.place(x=56, y=14)

        # --- 描述（height=3 保证最多 3 行空间） ---
        desc_label = tk.Label(card, text=tool_data["desc"], font=self.f_card_desc,
                              bg=Theme.BG_CARD, fg=Theme.TEXT_HINT,
                              anchor="nw", justify=tk.LEFT, wraplength=195, height=3)
        desc_label.place(x=56, y=44)

        # --- 启动按钮 ---
        btn = tk.Button(card, text="启动", font=self.f_card_name,
                        bg=Theme.ACCENT, fg=Theme.TEXT_WHITE,
                        relief=tk.FLAT, cursor="hand2", bd=0,
                        activebackground=Theme.ACCENT_DEEP,
                        activeforeground=Theme.TEXT_WHITE,
                        command=lambda t=tool_data: self.launch_tool(t))
        btn.place(x=self.CARD_W - 82, y=self.CARD_H - 38, width=64, height=28)

        # --- 绑定 hover 事件 ---
        card.bind("<Enter>", lambda e, c=card, b=accent_bar: self._card_enter(c, b))
        card.bind("<Leave>", lambda e, c=card, b=accent_bar: self._card_leave(c, b))
        # 子组件也绑定点击
        for w in (icon_canvas, name_label, desc_label, badge):
            w.bind("<Button-1>", lambda e, t=tool_data: self.launch_tool(t))
            w.bind("<Enter>", lambda e, c=card, b=accent_bar: self._card_enter(c, b))
            w.bind("<Leave>", lambda e, c=card, b=accent_bar: self._card_leave(c, b))

        return card

    def _card_enter(self, card, bar):
        """hover 入"""
        card.configure(highlightbackground=Theme.ACCENT, highlightthickness=2)
        bar.configure(bg=Theme.ACCENT_DEEP)

    def _card_leave(self, card, bar):
        """hover 出"""
        card.configure(highlightbackground=Theme.BORDER, highlightthickness=1)
        bar.configure(bg=Theme.ACCENT)

    # ---- 鼠标滚轮 ----
    def _bind_mousewheel(self):
        def _wheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.canvas.bind_all("<MouseWheel>", _wheel, add="+")

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    # ---- 状态栏 ----
    def _update_status(self, searching=False):
        gui_n = sum(1 for t in self.all_tools if t.get("ui", "gui") == "gui")
        cli_n = sum(1 for t in self.all_tools if t.get("ui", "gui") == "cli")
        total = len(self.all_tools)
        base = f"共 {total} 个工具  |  GUI 界面: {gui_n}  |  命令行: {cli_n}"
        if searching:
            visible = sum(1 for cat, f in self._category_frames.items()
                          for c in f.winfo_children() if c.winfo_ismapped())
            base += f"  |  当前可见: {visible}"
        self.status_label.configure(text=base)

    # ---- 工具启动 ----
    def launch_tool(self, tool_data):
        # 配置里写的是相对项目根目录的路径，无论从哪里启动都能找到
        tool_path = os.path.join(PROJECT_ROOT, tool_data["path"])

        if not os.path.exists(tool_path):
            messagebox.showerror("错误", f"工具文件不存在:\n{tool_path}\n\n请检查文件路径是否正确。")
            return

        self._show_toast(tool_data["name"])

        def _launch():
            try:
                if tool_path.endswith('.html'):
                    abs_path = os.path.abspath(tool_path)
                    webbrowser.open(f'file:///{abs_path}')
                    return
                venv_python = tool_data.get("venv")
                if venv_python and os.path.exists(venv_python):
                    subprocess.Popen([venv_python, tool_path], cwd=PROJECT_ROOT)
                else:
                    subprocess.Popen([sys.executable, tool_path], cwd=PROJECT_ROOT)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"启动失败：{str(e)}"))

        threading.Thread(target=_launch, daemon=True).start()

    def _show_toast(self, tool_name):
        """轻量 toast 提示"""
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=Theme.TEXT_ONCARD)

        inner = tk.Frame(toast, bg=Theme.ACCENT, padx=24, pady=10)
        inner.pack()

        tk.Label(inner, text="✓", font=("Microsoft YaHei", 14, "bold"),
                 bg=Theme.ACCENT, fg=Theme.TEXT_WHITE).pack(side=tk.LEFT)
        tk.Label(inner, text=f"  正在启动：{tool_name}",
                 font=("Microsoft YaHei", 11), bg=Theme.ACCENT,
                 fg=Theme.TEXT_WHITE).pack(side=tk.LEFT)

        # 居中于父窗口
        toast.update_idletasks()
        px = self.root.winfo_x() + (self.root.winfo_width() - toast.winfo_width()) // 2
        py = self.root.winfo_y() + self.root.winfo_height() - toast.winfo_height() - 60
        toast.geometry(f"+{px}+{py}")

        toast.after(2500, toast.destroy)


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = ToolkitLauncher(root)
    root.mainloop()
