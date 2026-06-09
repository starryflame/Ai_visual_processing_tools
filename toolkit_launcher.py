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

# 工具配置数据
# 所有工具现在统一放在 tools/ 目录下，按功能分类
# ui 字段: "gui" = 完整图形界面, "cli" = 命令行/脚本 (无交互界面)
TOOLS_CONFIG = {
    "🏷️ 打标 / 标签": [
        {
            "name": "图片打标器 (主程序)",
            "path": "tools/tagging/image_tagger/main.py",
            "desc": "缩略图网格浏览、标签增删改查、AI提示词生成、批量打标、导出重命名",
            "icon": "🖼️",
            "ui": "gui"
        },
        {
            "name": "视频打标器",
            "path": "tools/tagging/video_tagger/code/video_tagger.py",
            "desc": "视频逐帧标记、AI标签生成、片段裁剪导出、标签预设管理",
            "icon": "🎬",
            "ui": "gui",
            "venv": "J:/Data/Ai_visual_processing_tools/video_mark_tool/.venv/Scripts/python.exe"
        },
        {
            "name": "标签预览管理器",
            "path": "tools/tagging/label_manager/pic_video_label_manager.py",
            "desc": "图片/视频混合浏览、标签编辑、拖拽导入、视频播放、双击快速删除",
            "icon": "📁",
            "ui": "gui"
        },
        {
            "name": "词频统计工具",
            "path": "tools/tagging/word_frequency/词频统计.py",
            "desc": "加载标签数据、词频统计排序、批量替换标签、AI重新生成标签",
            "icon": "📊",
            "ui": "gui"
        },
        {
            "name": "图片视频标签过滤",
            "path": "tools/tagging/label_filter/label_filter_ui.py",
            "desc": "缩略图网格浏览、按标签筛选图片/视频、多选批量导出或删除",
            "icon": "🏷️",
            "ui": "gui"
        },
        {
            "name": "数据集标签提取",
            "path": "tools/tagging/label_extractor/label_extractor.py",
            "desc": "从数据集目录递归收集所有txt标签文件，汇总合并为单一文本文件",
            "icon": "🏷️",
            "ui": "cli"
        }
    ],
    "🖼️ 图片处理": [
        {
            "name": "图片缩放工具",
            "path": "tools/image_processing/image_resizer/image_resizer.py",
            "desc": "拖拽导入图片、批量压缩到指定文件大小、质量/分辨率调节、格式转换",
            "icon": "📐",
            "ui": "gui"
        },
        {
            "name": "图片过滤工具",
            "path": "tools/image_processing/image_filter/main.py",
            "desc": "用AI视觉模型按自定义条件筛选图片、双栏YES/NO分类、一键导出",
            "icon": "🔍",
            "ui": "gui"
        },
        {
            "name": "图片批量裁剪 (网页版)",
            "path": "tools/image_processing/image_crop/batch_image_crop_offline.html",
            "desc": "浏览器内运行、多比例裁剪预设、拖拽导入、暗色模式、ZIP打包导出",
            "icon": "✂️",
            "ui": "gui"
        }
    ],
    "🎬 视频处理": [
        {
            "name": "视频转图片",
            "path": "tools/video_processing/video_to_image/视频转图片.py",
            "desc": "批量将视频逐帧导出为图片序列、支持webp/mp4等格式、多线程加速",
            "icon": "🎞️",
            "ui": "cli",
            "venv": "J:/Data/Ai_visual_processing_tools/video_mark_tool/.venv/Scripts/python.exe"
        },
        {
            "name": "视频拆分工具",
            "path": "tools/video_processing/video_splitter/通用拆分视频.py",
            "desc": "按指定秒数将视频切分为多个片段、保留音频、使用ffmpeg精确切割",
            "icon": "✂️",
            "ui": "cli"
        },
        {
            "name": "视频时长扩充",
            "path": "tools/video_processing/video_extender/扩充视频时长.py",
            "desc": "将短视频通过慢放拉伸到目标时长(默认5秒)、固定帧率输出",
            "icon": "⏱️",
            "ui": "cli"
        },
        {
            "name": "批量修改帧率",
            "path": "tools/video_processing/frame_rate_changer/frame_rate_changer.py",
            "desc": "用ffmpeg批量调整视频FPS(默认30fps)、保留音频流、支持多种格式",
            "icon": "⚡",
            "ui": "cli"
        }
    ],
    "🔗 配对工具": [
        {
            "name": "图片配对工具",
            "path": "tools/pairing/image_pairing/main.py",
            "desc": "双面板图片浏览、AI视觉模型自动配对人物、配对预览拼接图、批量导出",
            "icon": "🔗",
            "ui": "gui"
        },
        {
            "name": "相似度配对工具",
            "path": "tools/pairing/similarity_pairing/main.py",
            "desc": "双面板图片浏览、感知哈希+颜色直方图计算相似度、自动匹配最相似图片",
            "icon": "🧩",
            "ui": "gui"
        }
    ],
    "🔄 格式转换": [
        {
            "name": "全能媒体转换器",
            "path": "tools/media_conversion/media_converter/transform.py",
            "desc": "图片/视频/音频格式互转、视频转GIF(可控帧率分辨率)、批量处理",
            "icon": "🔄",
            "ui": "gui"
        },
        {
            "name": "改音频文件后缀",
            "path": "tools/media_conversion/music_kmg/music_kmg.py",
            "desc": "扫描目录下所有 .kgm.flac 文件，批量重命名为 .kgm 后缀",
            "icon": "🔓",
            "ui": "cli"
        }
    ],
    "📂 文件处理": [
        {
            "name": "文件夹批处理工具",
            "path": "tools/file_operations/folder_batch/folder_batch.py",
            "desc": "拆分大文件夹(保持图片/标签配对)、扁平化子目录、随机打乱文件名",
            "icon": "📂",
            "ui": "gui"
        },
        {
            "name": "批量改文件名",
            "path": "tools/file_operations/batch_rename/batch_rename.py",
            "desc": "批量删除文件名中的特定后缀(_real/_fake/_hd/_sd)，支持扩展后缀列表",
            "icon": "✏️",
            "ui": "cli"
        },
        {
            "name": "TXT 逗号分隔转换",
            "path": "tools/file_operations/txt_formatter/txt_formatter.py",
            "desc": "批量将TXT文件中中文逗号(，)替换为英文逗号(,)并删除所有空格",
            "icon": "📝",
            "ui": "cli"
        }
    ],
    "🎵 音频工具": [
        {
            "name": "多段音频拼接",
            "path": "tools/audio/audio_merger/audio_merger_gui.py",
            "desc": "多段音频合并拼接、支持按名称/修改时间排序、可选输出格式(mp3/wav/flac等)",
            "icon": "🎵",
            "ui": "gui"
        },
        {
            "name": "TTS 文字转语音",
            "path": "tools/audio/tts/qwen3tts/gradio的tts.py",
            "desc": "Qwen3TTS语音合成、多音色可选(御姐/萝莉/老男人等)、Gradio客户端调用",
            "icon": "🗣️",
            "ui": "gui"
        }
    ],
    "🎨 ComfyUI AI 工具": [
        {
            "name": "批量动漫转写实",
            "path": "tools/comfyui/batch_anime2real.py",
            "desc": "连接ComfyUI批量将动漫图转为写实风格、实时预览、支持多工作流切换",
            "icon": "🎨",
            "ui": "gui"
        },
        {
            "name": "批量图片放大",
            "path": "tools/comfyui/batch_image_upscale.py",
            "desc": "连接ComfyUI使用SeedVR2模型批量放大图片、分辨率控制、断点续传",
            "icon": "🔍",
            "ui": "gui"
        },
        {
            "name": "真人转动漫",
            "path": "tools/comfyui/真人转动漫.py",
            "desc": "连接ComfyUI使用LoRA将真人照片转为动漫风格、实时预览、半自动模式",
            "icon": "👤",
            "ui": "gui"
        },
        {
            "name": "Wan22 视频放大",
            "path": "tools/comfyui/wan22放大.py",
            "desc": "连接ComfyUI使用Wan2.2模型对视频进行高清放大处理",
            "icon": "⬆️",
            "ui": "cli"
        },
        {
            "name": "提示词提取",
            "path": "tools/comfyui/提示词提取.py",
            "desc": "从ComfyUI生成的PNG图片或视频文件中提取工作流提示词(节点113文本)",
            "icon": "💬",
            "ui": "cli"
        },
        {
            "name": "插帧工具",
            "path": "tools/comfyui/插帧.py",
            "desc": "连接ComfyUI使用VHS节点对视频进行帧间插值、提升流畅度",
            "icon": "🎬",
            "ui": "cli"
        }
    ]
}


class ToolkitLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 视觉处理工具集")
        self.root.geometry("900x700")

        # 设置最小尺寸
        self.root.minsize(800, 600)

        self.setup_style()
        self.setup_ui()

    def setup_style(self):
        """设置样式"""
        self.colors = {
            "bg_primary": "#1a1a2e",
            "bg_secondary": "#16213e",
            "bg_card": "#0f3460",
            "accent": "#e94560",
            "text_primary": "#ffffff",
            "text_secondary": "#a0a0a0",
            "button_hover": "#1f4068"
        }

        # 配置样式
        style = ttk.Style()
        style.theme_use('clam')

        # 自定义字体
        self.title_font = font.Font(family="Microsoft YaHei", size=18, weight="bold")
        self.desc_font = font.Font(family="Microsoft YaHei", size=10)
        self.btn_font = font.Font(family="Microsoft YaHei", size=11)

    def setup_ui(self):
        """设置界面"""
        # 主容器
        main_frame = tk.Frame(self.root, bg=self.colors["bg_primary"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题区域
        header_frame = tk.Frame(main_frame, bg=self.colors["bg_secondary"], height=80)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="🚀 AI 视觉处理工具集",
            font=("Microsoft YaHei", 24, "bold"),
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"]
        )
        title_label.pack(pady=20)

        subtitle = tk.Label(
            header_frame,
            text="点击工具卡片启动对应工具",
            font=("Microsoft YaHei", 10),
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_secondary"]
        )
        subtitle.pack()

        # 创建 Canvas 和滚动条
        self.canvas = tk.Canvas(main_frame, bg=self.colors["bg_primary"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.canvas.yview)

        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["bg_primary"])
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        # 绑定鼠标滚轮
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)

        # 绑定 Canvas 大小变化
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # 构建工具分类
        self.build_tool_categories()

        # 底部状态栏
        status_frame = tk.Frame(main_frame, bg=self.colors["bg_secondary"], height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)

        gui_count = self.count_tools_by_ui("gui")
        cli_count = self.count_tools_by_ui("cli")
        status_label = tk.Label(
            status_frame,
            text=f"共 {self.count_tools()} 个工具  |  GUI 界面: {gui_count}  |  命令行脚本: {cli_count}",
            font=("Microsoft YaHei", 9),
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_secondary"]
        )
        status_label.pack(side=tk.LEFT, padx=10)

    def _on_mousewheel(self, event):
        """鼠标滚轮事件"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_canvas_configure(self, event):
        """Canvas 大小变化时调整内部框架宽度"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def count_tools(self):
        """统计工具总数"""
        count = 0
        for category, tools in TOOLS_CONFIG.items():
            count += len(tools)
        return count

    def count_tools_by_ui(self, ui_type):
        """统计指定 UI 类型的工具数量"""
        count = 0
        for category, tools in TOOLS_CONFIG.items():
            for tool in tools:
                if tool.get("ui", "gui") == ui_type:
                    count += 1
        return count

    def build_tool_categories(self):
        """构建所有工具分类"""
        row = 0

        for category, tools in TOOLS_CONFIG.items():
            # 分类标题
            category_frame = tk.Frame(self.scrollable_frame, bg=self.colors["bg_primary"])
            category_frame.pack(fill=tk.X, padx=20, pady=(20, 10))

            category_label = tk.Label(
                category_frame,
                text=f"📌 {category}",
                font=("Microsoft YaHei", 14, "bold"),
                bg=self.colors["bg_primary"],
                fg=self.colors["accent"]
            )
            category_label.pack(anchor="w")

            # 工具卡片容器
            cards_frame = tk.Frame(self.scrollable_frame, bg=self.colors["bg_primary"])
            cards_frame.pack(fill=tk.X, padx=20, pady=5)

            # 创建工具卡片
            for i, tool in enumerate(tools):
                card = self.create_tool_card(cards_frame, tool)
                card.pack(side=tk.LEFT, padx=5, pady=5)

    def create_tool_card(self, parent, tool_data):
        """创建工具卡片"""
        card = tk.Frame(
            parent,
            bg=self.colors["bg_card"],
            width=250,
            height=130
        )
        card.pack_propagate(False)

        # 绑定鼠标事件
        card.bind("<Enter>", lambda e, c=card: self.on_card_enter(c))
        card.bind("<Leave>", lambda e, c=card: self.on_card_leave(c))
        card.bind("<Button-1>", lambda e, t=tool_data: self.launch_tool(t))

        # 图标
        icon_label = tk.Label(
            card,
            text=tool_data["icon"],
            font=("Segoe UI Emoji", 24),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"]
        )
        icon_label.place(x=15, y=15)

        # UI 类型徽章 (右上角)
        ui_type = tool_data.get("ui", "gui")
        if ui_type == "gui":
            badge_text = "GUI"
            badge_bg = "#1a7f3f"    # 绿色 - 有图形界面
            badge_fg = "#dcfce7"
        else:
            badge_text = "脚本"
            badge_bg = "#7f6a1a"    # 琥珀色 - 命令行脚本
            badge_fg = "#fef9c3"
        badge = tk.Label(
            card,
            text=badge_text,
            font=("Microsoft YaHei", 8, "bold"),
            bg=badge_bg,
            fg=badge_fg,
            padx=6,
            pady=1
        )
        badge.place(x=188, y=8)

        # 工具名称
        name_label = tk.Label(
            card,
            text=tool_data["name"],
            font=("Microsoft YaHei", 11, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            wraplength=175,
            anchor="w"
        )
        name_label.place(x=60, y=20)

        # 工具描述
        desc_label = tk.Label(
            card,
            text=tool_data["desc"],
            font=self.desc_font,
            bg=self.colors["bg_card"],
            fg=self.colors["text_secondary"],
            wraplength=175,
            anchor="w",
            justify=tk.LEFT
        )
        desc_label.place(x=60, y=50)

        # 启动按钮
        btn = tk.Button(
            card,
            text="启动",
            font=self.btn_font,
            bg=self.colors["accent"],
            fg=self.colors["text_primary"],
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda t=tool_data: self.launch_tool(t)
        )
        btn.place(x=170, y=85, width=65, height=25)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg="#ff6b6b"))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=self.colors["accent"]))

        return card

    def on_card_enter(self, card):
        """鼠标移入卡片"""
        card.configure(bg=self.colors["button_hover"])
        for child in card.winfo_children():
            if isinstance(child, tk.Label):
                child_bg = child.cget("bg")
                if child_bg == self.colors["bg_card"]:
                    child.configure(bg=self.colors["button_hover"])

    def on_card_leave(self, card):
        """鼠标移出卡片"""
        card.configure(bg=self.colors["bg_card"])
        for child in card.winfo_children():
            if isinstance(child, tk.Label):
                child_bg = child.cget("bg")
                if child_bg == self.colors["button_hover"]:
                    child.configure(bg=self.colors["bg_card"])

    def launch_tool(self, tool_data):
        """启动工具"""
        tool_path = tool_data["path"]

        # 检查文件是否存在
        if not os.path.exists(tool_path):
            messagebox.showerror(
                "错误",
                f"工具文件不存在:\n{tool_path}\n\n请检查文件路径是否正确。"
            )
            return

        # 显示启动提示
        self.show_launching_dialog(tool_data["name"])

        # 在新线程中启动工具
        def _launch():
            try:
                # HTML 文件用浏览器打开
                if tool_path.endswith('.html'):
                    abs_path = os.path.abspath(tool_path)
                    webbrowser.open(f'file:///{abs_path}')
                    return
                # 检查是否有指定的虚拟环境
                venv_python = tool_data.get("venv")
                if venv_python and os.path.exists(venv_python):
                    subprocess.Popen([venv_python, tool_path], cwd=os.getcwd())
                else:
                    subprocess.Popen([sys.executable, tool_path], cwd=os.getcwd())
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"启动失败：{str(e)}"))

        thread = threading.Thread(target=_launch, daemon=True)
        thread.start()

    def show_launching_dialog(self, tool_name):
        """显示启动中对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("提示")
        dialog.geometry("300x100")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中
        x = (self.root.winfo_screenwidth() - 300) // 2
        y = (self.root.winfo_screenheight() - 100) // 2
        dialog.geometry(f"300x100+{x}+{y}")

        label = tk.Label(
            dialog,
            text=f"正在启动：{tool_name}\n请稍候...",
            font=("Microsoft YaHei", 12),
            pady=20
        )
        label.pack()

        # 2 秒后自动关闭
        def close_dialog():
            try:
                dialog.destroy()
            except:
                pass

        self.root.after(2000, close_dialog)


if __name__ == "__main__":
    root = tk.Tk()
    app = ToolkitLauncher(root)
    root.mainloop()
