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

    # 优先尝试本地模型，失败后再尝试vLLM API
    try:
        self._generate_ai_caption_local()
    except Exception as local_error:
        print(f"本地模型生成失败: {local_error}")
        try:
            self._generate_ai_caption_vllm()
        except Exception as vllm_error:
            messagebox.showerror("错误", f"本地模型和vLLM API均调用失败\n本地错误: {str(local_error)}\nvLLM错误: {str(vllm_error)}")


# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['generate_ai_caption']
