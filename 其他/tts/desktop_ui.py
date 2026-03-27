"""
TTS 前端界面 - Tkinter Desktop UI
基于 gradio_client 调用本地 TTS 服务
无需 Web 服务器，纯桌面应用
"""
import tkinter as tk
from tkinter import ttk, messagebox
from gradio_client import Client
import os
import winsound

# 连接到本地 TTS 服务
client = Client("http://localhost:7862/")

# 可用的音色列表
VOICES = [
    "御姐",
    "萝莉1", 
    "老男人",
    "少女音1",
    "少女音2",
    "少女音3"
]


class TTSGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎙️ TTS 语音合成工具")
        self.root.geometry("700x700")
        self.root.resizable(True, True)
        
        # 样式配置
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
    
    def setup_styles(self):
        """设置 UI 样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 按钮样式
        style.configure('Primary.TButton', font=('Microsoft YaHei UI', 12, 'bold'))
        style.configure('Secondary.TButton', font=('Microsoft YaHei UI', 10))
    
    def create_widgets(self):
        """创建控件"""
        
        # 标题
        title_label = ttk.Label(
            self.root, 
            text="🎙️ TTS 语音合成工具",
            font=('Microsoft YaHei UI', 20, 'bold')
        )
        title_label.pack(pady=15)
        
        # 副标题
        subtitle = ttk.Label(
            self.root,
            text="输入文字，选择音色和参数，生成并播放语音",
            font=('Microsoft YaHei UI', 10)
        )
        subtitle.pack(pady=(0, 20))
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧：输入区域
        left_frame = ttk.LabelFrame(main_frame, text="📥 文字输入", padding=10)
        left_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=5)
        
        # 右侧：输出区域
        right_frame = ttk.LabelFrame(main_frame, text="🎧 输出结果", padding=10)
        right_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0), pady=5)
        
        # 配置网格权重
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        left_frame.rowconfigure(2, weight=1)
        
        # ========== 左侧输入区域 ==========
        
        # 音色选择
        ttk.Label(left_frame, text="🎤 音色：").grid(row=0, column=0, sticky='w', pady=(0, 5))
        self.voice_var = tk.StringVar(value="少女音1")
        voice_combo = ttk.Combobox(
            left_frame, 
            textvariable=self.voice_var,
            values=VOICES,
            width=24,
            state='readonly'
        )
        voice_combo.grid(row=0, column=1, sticky='ew', pady=(0, 5))
        
        # 文字输入框
        ttk.Label(left_frame, text="📝 文字内容：").grid(row=1, column=0, sticky='nw', pady=(10, 3))
        self.text_text = tk.Text(
            left_frame, 
            height=8, 
            width=40,
            font=('Microsoft YaHei UI', 11)
        )
        self.text_text.grid(row=1, column=1, sticky='nsew')
        
        # 高级设置按钮
        self.advanced_var = tk.BooleanVar(value=False)
        advanced_check = ttk.Checkbutton(
            left_frame, 
            text="⚙️ 显示高级参数",
            variable=self.advanced_var,
            command=self.toggle_advanced
        )
        advanced_check.grid(row=2, column=0, columnspan=2, pady=(10, 5), sticky='w')
        
        # 高级设置框架（默认隐藏）
        self.advanced_frame = ttk.LabelFrame(main_frame, text="⚙️ 高级参数", padding=10)
        self.advanced_frame.grid(row=1, column=0, columnspan=2, sticky='nsew', pady=(5, 5))
        
        # 语速设置
        ttk.Label(self.advanced_frame, text="⏱️ 语速：").grid(row=0, column=0, sticky='w', pady=5)
        self.speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(
            self.advanced_frame, 
            from_=0.5, 
            to=2.0, 
            orient=tk.HORIZONTAL,
            variable=self.speed_var,
            length=200
        )
        speed_scale.grid(row=0, column=1, sticky='ew', padx=(10, 0))
        
        # 分块大小
        ttk.Label(self.advanced_frame, text="📦 分块大小：").grid(row=1, column=0, sticky='w', pady=5)
        self.chunk_var = tk.IntVar(value=900)
        chunk_scale = ttk.Scale(
            self.advanced_frame, 
            from_=500, 
            to=2000, 
            orient=tk.HORIZONTAL,
            variable=self.chunk_var,
            length=200
        )
        chunk_scale.grid(row=1, column=1, sticky='ew', padx=(10, 0))
        
        # 温度参数
        ttk.Label(self.advanced_frame, text="🌡️ 温度：").grid(row=2, column=0, sticky='w', pady=5)
        self.temp_var = tk.DoubleVar(value=0.1)
        temp_scale = ttk.Scale(
            self.advanced_frame, 
            from_=0.1, 
            to=1.0, 
            orient=tk.HORIZONTAL,
            variable=self.temp_var,
            length=200
        )
        temp_scale.grid(row=2, column=1, sticky='ew', padx=(10, 0))
        
        # ========== 右侧输出区域 ==========
        
        # 音频显示区域（文本形式）
        ttk.Label(right_frame, text="🎧 生成的音频：").pack(anchor='w', pady=(0, 5))
        self.audio_path = tk.StringVar(value="等待生成...")
        audio_label = ttk.Label(
            right_frame, 
            textvariable=self.audio_path,
            wraplength=300,
            font=('Microsoft YaHei UI', 10),
            foreground='gray'
        )
        audio_label.pack(anchor='w')
        
        # 状态信息
        ttk.Label(right_frame, text="💬 状态：").pack(anchor='w', pady=(20, 5))
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(
            right_frame, 
            textvariable=self.status_var,
            wraplength=300,
            font=('Microsoft YaHei UI', 10)
        )
        status_label.pack(anchor='w')
        
        # ========== 底部按钮区域 ==========
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(15, 0))
        
        # 生成按钮
        self.generate_btn = ttk.Button(
            btn_frame, 
            text="🚀 生成语音", 
            command=self.generate_speech,
            style='Primary.TButton'
        )
        self.generate_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 播放按钮
        self.play_btn = ttk.Button(
            btn_frame, 
            text="▶️ 播放音频", 
            command=self.play_audio,
            style='Secondary.TButton'
        )
        self.play_btn.pack(side=tk.LEFT)
    
    def toggle_advanced(self):
        """切换高级参数显示"""
        if self.advanced_var.get():
            self.advanced_frame.grid()
        else:
            self.advanced_frame.grid_remove()
    
    def play_audio(self):
        """播放音频文件"""
        audio_path = self.audio_path.get()
        
        if audio_path and "生成" in audio_path and not os.path.exists(audio_path):
            messagebox.showwarning("警告", "请先点击「生成语音」按钮！")
            return
        
        if os.path.exists(audio_path):
            winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.status_var.set("🔊 正在播放...")
        else:
            messagebox.showerror("错误", "未找到音频文件！")
    
    def generate_speech(self):
        """生成语音"""
        text = self.text_text.get("1.0", tk.END).strip()
        
        if not text:
            messagebox.showwarning("警告", "请输入要转换的文字！")
            return
        
        # 更新状态
        self.status_var.set("⏳ 正在生成中...")
        self.root.update()
        self.generate_btn.config(state=tk.DISABLED)
        
        try:
            result = client.predict(
                voices_dropdown=self.voice_var.get(),
                text=text,
                prompt_text="",
                prompt_audio=None,
                speed=float(self.speed_var.get()),
                chunk_size=int(self.chunk_var.get()),
                batch=25,
                lang="Auto",
                model_type="1.7B",
                temperature=float(self.temp_var.get()),
                auto_up=False,
                api_name="/do_job"
            )
            
            audio_path = result[0] if isinstance(result, tuple) else result
            
            # 更新显示
            self.audio_path.set(audio_path)
            self.status_var.set(f"✅ 生成成功！")
            
            # 自动播放
            if os.path.exists(audio_path):
                winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.status_var.set("🔊 正在播放...")
        
        except Exception as e:
            self.audio_path.set("❌ 生成失败")
            self.status_var.set(f"错误：{str(e)}")
            messagebox.showerror("错误", f"语音生成失败：\n{str(e)}")
        
        finally:
            self.generate_btn.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    
    # 居中显示
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - 700) // 2
    y = (screen_height - 500) // 2
    root.geometry(f"700x500+{x}+{y}")
    
    app = TTSGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
