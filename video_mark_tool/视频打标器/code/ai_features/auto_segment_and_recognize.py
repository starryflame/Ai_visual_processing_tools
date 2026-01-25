import tkinter as tk
from tkinter import messagebox
import time
import cv2

def auto_segment_and_recognize(self):
    """自动读取视频文件列表并使用AI识别生成标签"""
    # 显示选择调用方式的窗口
    method_window = tk.Toplevel(self.root)
    method_window.title("自动读取视频文件列表并使用AI识别生成标签")
    method_window.geometry("300x150")
    method_window.transient(self.root)
    method_window.grab_set()
    
    # 居中显示
    method_window.update_idletasks()
    x = (method_window.winfo_screenwidth() // 2) - (300 // 2)
    y = (method_window.winfo_screenheight() // 2) - (150 // 2)
    method_window.geometry(f"300x150+{x}+{y}")

    # 添加进度信息显示标签
    progress_label = tk.Label(method_window, text="准备开始处理...", wraplength=280)
    progress_label.pack(pady=20)

    # 添加取消按钮
    cancel_button = tk.Button(method_window, text="取消", command=lambda: method_window.destroy())
    cancel_button.pack(pady=10)

    def batch_process_videos():
        """批量处理视频文件列表中的所有视频"""
        if not hasattr(self, 'video_list') or not self.video_list:
            messagebox.showwarning("警告", "没有找到视频文件列表")
            method_window.destroy()
            return

        # 记录开始时间
        start_time = time.time()
        processed_count = 0
        total_videos = len(self.video_list)

        for idx, video_path in enumerate(self.video_list):
            try:
                # 更新进度信息
                progress_info = f"正在处理第 {idx + 1}/{total_videos} 个视频: {video_path}"
                # 在GUI窗口中更新进度信息
                self.root.after(0, lambda info=progress_info: progress_label.config(text=info))
                print(progress_info)
                
                # 释放之前的视频捕获对象
                if self.cap:
                    self.cap.release()

                # 清空之前处理的帧
                self.processed_frames = []
                self.frames_loaded = False
                self.tags = []  # 清空标记
                self.excluded_segments = []  # 清空排除片段
                self.current_frame_idx = 0

                # 加载当前视频
                self.video_path = video_path
                # 预处理所有帧
                self.preprocess_frames()
                
                self.cap = cv2.VideoCapture(self.video_path)
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.fps = self.cap.get(cv2.CAP_PROP_FPS)
                self.current_frame = 0
                self.start_frame = 0
                self.end_frame = self.total_frames - 1

                #self.add_tag()  # 初始化一个标签范围覆盖整个视频
                # 调用AI生成标签（使用本地Ollama模型）
                # 调用AI生成新标签
                new_caption = self._generate_single_tag_caption()

                if new_caption:  # 如果成功生成了新标签
                    # 创建新的标签信息并添加到标签列表
                    new_tag_info = {
                        "start": self.start_frame,
                        "end": self.end_frame,
                        "tag": new_caption
                    }
                    self.tags = []
                    self.tags.append(new_tag_info)
                    print(f"已添加新标签: {new_caption}")
                    # 更新列表框中的显示
                    self.tag_listbox.delete(0, tk.END)  # 清空列表框
                    self.root.after(0, lambda s=self.start_frame, e=self.end_frame, c=new_caption:
                                   self.tag_listbox.insert(tk.END, f"帧 {s}-{e}: {c}"))

                self.export_tags()  # 导出当前视频的标签
                # 等待AI处理完成（这里可以根据实际情况调整等待逻辑）
                time.sleep(1)  # 简单延迟，实际应用中可能需要更复杂的同步机制
                
                processed_count += 1
                print(f"已完成处理: {video_path}")
                
            except Exception as e:
                print(f"处理视频 {video_path} 时出错: {str(e)}")
                continue
        
        # 处理完成后显示统计信息
        elapsed_time = time.time() - start_time
        result_msg = f"批量处理完成!\n共处理 {processed_count}/{total_videos} 个视频\n总耗时: {elapsed_time:.2f} 秒"
        print(result_msg)
        
        # 在主线程中显示完成消息
        self.root.after(0, lambda: messagebox.showinfo("批量处理完成", result_msg))
        # 更新进度标签为完成状态
        self.root.after(0, lambda: progress_label.config(text=result_msg.replace('\n', ' ')))
        
        # 关闭方法选择窗口
        self.root.after(0, lambda: method_window.destroy())

    # 创建选择窗口
    batch_process_videos()

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['auto_segment_and_recognize']