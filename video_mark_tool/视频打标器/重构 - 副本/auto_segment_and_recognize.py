# This is a method from class VideoTagger
import tkinter as tk


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

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['auto_segment_and_recognize']
