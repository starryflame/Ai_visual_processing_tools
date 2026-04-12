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

# 工具配置数据
TOOLS_CONFIG = {
    "图片打标工具": [
        {
            "name": "图片打标器 (主程序)",
            "path": "pictures_mark_tool/main.py",
            "desc": "PyQt5 图片浏览、标签管理、AI 提示词生成",
            "icon": "🖼️"
        },
        {
            "name": "词频统计工具",
            "path": "pictures_mark_tool/tool/词频统计/词频统计.py",
            "desc": "标签词频分析、批量替换、AI 重新生成",
            "icon": "📊"
        }
    ],
    "视频打标工具": [
        {
            "name": "视频打标器",
            "path": "video_mark_tool/视频打标器/code/video_tagger.py",
            "desc": "视频帧标记、AI 标签生成、片段导出",
            "icon": "🎬",
            "venv": "J:/Data/Ai_visual_processing_tools/video_mark_tool/.venv/Scripts/python.exe"
        }
    ],
    "文件处理工具": [
        {
            "name": "图像视频标签管理器",
            "path": "其他/图像视频标签预览/pic_video_label_manager.py",
            "desc": "视频播放、图片预览、标签编辑",
            "icon": "📁"
        },
        {
            "name": "文件夹批处理工具",
            "path": "其他/文件处理/文件夹通用处理_GUI.py",
            "desc": "拆分大文件夹、扁平化、打乱名称",
            "icon": "📂"
        },
        {
            "name": "图片配对工具",
            "path": "其他/文件处理/配对工具/main.py",
            "desc": "双面板对比、自动配对、导出配对",
            "icon": "🔗"
        }
    ],
    "格式转换工具": [
        {
            "name": "图片转视频",
            "path": "其他/格式转换/图片转视频.py",
            "desc": "批量图片转单帧 MP4",
            "icon": "🎞️"
        },
        {
            "name": "全能媒体转换器",
            "path": "其他/格式转换/transform.py",
            "desc": "图片/视频/音频格式互转",
            "icon": "🔄"
        }
    ],
    "ComfyUI 工具": [
        {
            "name": "批量动漫转写实",
            "path": "其他/comfyui/batch_anime2real.py",
            "desc": "批量处理、实时预览",
            "icon": "🎨"
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

        status_label = tk.Label(
            status_frame,
            text=f"共 {self.count_tools()} 个工具可用",
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
            height=120
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

        # 工具名称
        name_label = tk.Label(
            card,
            text=tool_data["name"],
            font=("Microsoft YaHei", 11, "bold"),
            bg=self.colors["bg_card"],
            fg=self.colors["text_primary"],
            wraplength=180,
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
            wraplength=180,
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
                if child.cget("bg") == self.colors["bg_card"]:
                    child.configure(bg=self.colors["button_hover"])

    def on_card_leave(self, card):
        """鼠标移出卡片"""
        card.configure(bg=self.colors["bg_card"])
        for child in card.winfo_children():
            if isinstance(child, tk.Label):
                if child.cget("bg") == self.colors["button_hover"]:
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
