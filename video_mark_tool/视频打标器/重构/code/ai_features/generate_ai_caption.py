# This is a method from class VideoTagger
import tkinter as tk
from tkinter import messagebox


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

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['generate_ai_caption']
