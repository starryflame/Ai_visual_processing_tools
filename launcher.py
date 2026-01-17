import sys
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import subprocess
# 添加time模块用于延迟
import time
# 添加用于生成requirements的模块
import pkg_resources

class ToolLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("AI视觉处理工具集")
        self.root.geometry("600x600")
        
        # 设置窗口居中
        self.center_window()
        
        self.setup_ui()
        
    def center_window(self):
        # 获取屏幕尺寸
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # 获取窗口尺寸
        window_width = 600
        window_height = 600
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
    def setup_ui(self):
        # 创建标题
        title_label = tk.Label(self.root, text="AI视觉处理工具集", font=("Microsoft YaHei", 20, "bold"))
        title_label.pack(pady=20)
        
        # 创建工具选择框架
        tools_frame = tk.Frame(self.root)
        tools_frame.pack(expand=True, fill=tk.BOTH, padx=50, pady=20)
        
        # 图片打标器按钮
        img_tag_btn = tk.Button(tools_frame, text="图片打标器", font=("Microsoft YaHei", 14),
                               command=self.launch_img_tagger, height=2, width=20,
                               bg="#4CAF50", fg="white")
        img_tag_btn.pack(pady=10)
        
        # 词频统计按钮
        word_freq_btn = tk.Button(tools_frame, text="词频统计", font=("Microsoft YaHei", 14),
                                 command=self.launch_word_freq, height=2, width=20,
                                 bg="#2196F3", fg="white")
        word_freq_btn.pack(pady=10)
        
        # 视频打标器按钮
        video_tag_btn = tk.Button(tools_frame, text="视频打标器", font=("Microsoft YaHei", 14),
                                 command=self.launch_video_tagger, height=2, width=20,
                                 bg="#FF9800", fg="white")
        video_tag_btn.pack(pady=10)
        
        # 视频标签编辑器按钮
        video_edit_btn = tk.Button(tools_frame, text="文件标签筛选编辑器", font=("Microsoft YaHei", 14),
                                  command=self.launch_video_editor, height=2, width=20,
                                  bg="#9C27B0", fg="white")
        video_edit_btn.pack(pady=10)
        
        # 生成requirements文件按钮
        requirements_btn = tk.Button(tools_frame, text="生成依赖文件", font=("Microsoft YaHei", 14),
                                   command=self.generate_requirements, height=2, width=20,
                                   bg="#607D8B", fg="white")
        requirements_btn.pack(pady=10)
        
        # 退出按钮
        exit_btn = tk.Button(self.root, text="退出", font=("Microsoft YaHei", 12),
                            command=self.root.quit, height=1, width=10,
                            bg="#f44336", fg="white")
        exit_btn.pack(pady=20)
        
    def launch_with_progress(self, launch_function):
        """
        带进度提示的启动函数
        """
        # 显示启动提示
        progress_window = tk.Toplevel(self.root)
        progress_window.title("提示")
        progress_window.geometry("300x100")
        progress_window.resizable(False, False)
        
        # 居中显示
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        screen_width = progress_window.winfo_screenwidth()
        screen_height = progress_window.winfo_screenheight()
        x = (screen_width - 300) // 2
        y = (screen_height - 100) // 2
        progress_window.geometry(f"300x100+{x}+{y}")
        
        label = tk.Label(progress_window, text="正在启动中，请稍候...", font=("Microsoft YaHei", 12))
        label.pack(expand=True)
        
        # 更新界面
        progress_window.update()
        
        try:
            # 执行启动函数
            launch_function()
            # 固定等待2秒
            time.sleep(2)
        except Exception as e:
            messagebox.showerror("错误", f"无法启动工具: {str(e)}")
        finally:
            # 关闭提示窗口
            progress_window.destroy()
            progress_window.update()
    
    def launch_img_tagger(self):
        def _launch():
            # 启动图片打标器
            subprocess.Popen([sys.executable, "pictures_mark_tool/main.py"])
        self.launch_with_progress(_launch)
            
    def launch_word_freq(self):
        def _launch():
            # 启动词频统计工具
            subprocess.Popen([sys.executable, "pictures_mark_tool/tool/词频统计/词频统计.py"])
        self.launch_with_progress(_launch)
            
    def launch_video_tagger(self):
        def _launch():
            # 启动视频打标器，使用指定的虚拟环境
            venv_python = "J:/Data/Ai_visual_processing_tools/video_mark_tool/.venv/Scripts/python.exe"
            if os.path.exists(venv_python):
                subprocess.Popen([venv_python, "video_mark_tool/视频打标器/重构/code/video_tagger.py"])
            else:
                # 如果虚拟环境不存在，回退到默认Python解释器
                subprocess.Popen([sys.executable, "video_mark_tool/视频打标器/重构/code/video_tagger.py"])
        self.launch_with_progress(_launch)
            
    def launch_video_editor(self):
        def _launch():
            # 启动视频标签编辑器
            subprocess.Popen([sys.executable, "video_mark_tool/图像视频标签预览ui/pic_video_label_manager.py"])
        self.launch_with_progress(_launch)
        
    def generate_requirements(self):
        """
        生成整个项目的requirements.txt文件
        """
        try:
            # 获取当前环境中已安装的所有包
            installed_packages = [d for d in pkg_resources.working_set]
            package_list = [f"{package.project_name}=={package.version}" for package in installed_packages]
            
            # 写入requirements.txt文件
            requirements_path = "J:/Data/Ai_visual_processing_tools/requirements.txt"
            with open(requirements_path, "w", encoding="utf-8") as f:
                f.write("# AI视觉处理工具集依赖文件\n")
                f.write("# 通过pip freeze方式生成\n\n")
                for package in sorted(package_list):
                    f.write(package + "\n")
            
            messagebox.showinfo("成功", f"依赖文件已生成至:\n{requirements_path}")
        except Exception as e:
            messagebox.showerror("错误", f"生成依赖文件失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ToolLauncher(root)
    root.mainloop()