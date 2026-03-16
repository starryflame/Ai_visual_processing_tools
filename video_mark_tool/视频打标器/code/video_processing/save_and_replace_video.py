import cv2
import os
import tkinter as tk
from tkinter import messagebox, ttk


def save_and_replace_video(app):
    """保存起始帧到末尾帧区间为新视频，替换原视频"""
    if not app.video_path:
        messagebox.showwarning("警告", "请先加载视频！")
        return
    
    if app.start_frame >= app.end_frame:
        messagebox.showwarning("警告", "请先设置有效的起始帧和结束帧（起始帧 < 结束帧）！")
        return
    
    # 确认操作
    confirm = messagebox.askyesno("确认", 
        f"将保存第 {app.start_frame} 帧到第 {app.end_frame} 帧的视频片段\n"
        f"并替换原视频文件：{os.path.basename(app.video_path)}\n\n"
        f"此操作不可逆，是否继续？")
    
    if not confirm:
        return
    
    try:
        # 获取导出帧率
        fps_str = app.export_fps.get()
        if fps_str == "原始帧率" or fps_str == "":
            output_fps = app.fps
        else:
            output_fps = float(fps_str)
        
        # 获取视频目录和文件名
        video_dir = os.path.dirname(app.video_path)
        video_name = os.path.basename(app.video_path)
        
        # 创建临时文件名
        temp_path = os.path.join(video_dir, f"_temp_{video_name}")
        
        # 打开视频进行读取
        cap = cv2.VideoCapture(app.video_path)
        if not cap.isOpened():
            messagebox.showerror("错误", "无法打开视频文件！")
            return
        
        # 获取视频属性
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, output_fps, (frame_width, frame_height))
        
        if not out.isOpened():
            messagebox.showerror("错误", "无法创建输出视频文件！")
            cap.release()
            return
        
        # 读取并写入指定帧区间
        cap.set(cv2.CAP_PROP_POS_FRAMES, app.start_frame)
        frames_written = 0
        total_frames = app.end_frame - app.start_frame
        
        progress_window = tk.Toplevel(app.root)
        progress_window.title("保存视频中...")
        progress_window.geometry("300x100")
        progress_window.transient(app.root)
        progress_window.grab_set()
        
        progress_label = tk.Label(progress_window, text=f"进度：0/{total_frames}", font=app.font)
        progress_label.pack(pady=10)
        progress_bar = ttk.Progressbar(progress_window, length=250, mode='determinate')
        progress_bar.pack(pady=5)
        progress_bar["maximum"] = total_frames
        
        app.root.update()
        
        while True:
            ret, frame = cap.read()
            if not ret or cap.get(cv2.CAP_PROP_POS_FRAMES) > app.end_frame:
                break
            
            out.write(frame)
            frames_written += 1
            
            # 更新进度
            progress_label.config(text=f"进度：{frames_written}/{total_frames}")
            progress_bar["value"] = frames_written
            if frames_written % 10 == 0:
                app.root.update()
        
        cap.release()
        out.release()
        
        progress_window.destroy()
        
        if frames_written == 0:
            messagebox.showerror("错误", "未能写入任何帧！")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return
        
        # 关闭当前视频
        if app.cap:
            app.cap.release()
            app.cap = None
        
        # 删除原文件，重命名临时文件
        os.remove(app.video_path)
        os.rename(temp_path, app.video_path)
        
        messagebox.showinfo("成功", f"视频已保存并替换！\n共保存 {frames_written} 帧")
        
    except Exception as e:
        messagebox.showerror("错误", f"保存视频时出错：{str(e)}")
        # 清理临时文件
        temp_path = os.path.join(os.path.dirname(app.video_path), f"_temp_{os.path.basename(app.video_path)}")
        if os.path.exists(temp_path):
            os.remove(temp_path)