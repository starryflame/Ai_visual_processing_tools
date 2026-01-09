# This is a method from class VideoTagger
import cv2
import os
from tkinter import filedialog, messagebox, simpledialog

def export_tags(self):
    if not self.tags:
        messagebox.showerror("错误", "没有标记需要导出")
        return
        
    # 选择导出目录
    export_dir = filedialog.askdirectory(title="选择导出目录")
    if not export_dir:
        return
        
    # 获取导出文件夹名称
    folder_name = simpledialog.askstring("导出文件夹名称", "请输入导出文件夹名称(留空则直接保存到当前文件夹):")
    
    # 如果用户取消输入对话框，则返回
    if folder_name is None:
        return
        
    # 如果输入了文件夹名称，则创建子文件夹，否则直接使用选中的文件夹
    if folder_name:
        # 处理非法字符
        safe_folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        # 限制文件夹名称长度
        safe_folder_name = safe_folder_name[:50] if len(safe_folder_name) > 50 else safe_folder_name
        # 替换空格为下划线
        safe_folder_name = safe_folder_name.replace(" ", "_")
        
        # 如果处理后名称为空，则使用默认名称
        if not safe_folder_name:
            safe_folder_name = "标记视频片段"
            
        # 检查是否重名并处理
        main_folder = os.path.join(export_dir, safe_folder_name)
        counter = 1
        original_main_folder = main_folder
        while os.path.exists(main_folder):
            main_folder = f"{original_main_folder}_{counter}"
            counter += 1
            
        os.makedirs(main_folder, exist_ok=True)
    else:
        # 直接使用选中的文件夹
        main_folder = export_dir
    
    # 获取导出帧率
    try:
        if self.fps_entry.get() == "原始帧率":
            export_fps = self.fps
        else:
            export_fps = float(self.fps_entry.get())
    except ValueError:
        messagebox.showerror("错误", "请输入有效的帧率数值")
        return
        
    # 创建主文件夹
    
    # 导出每个标记片段
    for i, tag in enumerate(self.tags):
        start_frame = tag["start"]
        end_frame = tag["end"]
        tag_text = tag["tag"]
        
        # 获取第一帧来确定尺寸
        if start_frame < len(self.processed_frames):
            first_frame = self.processed_frames[start_frame]
            height, width = first_frame.shape[:2]
            
            # 生成安全的文件名，移除或替换非法字符
            safe_tag_text = "".join(c for c in tag_text if c.isalnum() or c in (' ', '-', '_')).rstrip()
            # 限制文件名长度
            safe_tag_text = safe_tag_text[:50] if len(safe_tag_text) > 50 else safe_tag_text
            # 替换空格为下划线
            safe_tag_text = safe_tag_text.replace(" ", "_")
            
            # 如果处理后的标签为空，则使用默认名称
            if not safe_tag_text:
                safe_tag_text = "untitled"
            
            # 生成文件名
            filename = f"video_{i+1:03d}_{safe_tag_text}"
            video_path = os.path.join(main_folder, f"{filename}.mp4")
            txt_path = os.path.join(main_folder, f"{filename}.txt")
            
            # 检查文件是否已存在，如果存在则添加序号
            counter = 1
            original_video_path = video_path
            original_txt_path = txt_path
            while os.path.exists(video_path) or os.path.exists(txt_path):
                filename = f"video_{i+1:03d}_{safe_tag_text}_{counter}"
                video_path = os.path.join(main_folder, f"{filename}.mp4")
                txt_path = os.path.join(main_folder, f"{filename}.txt")
                counter += 1
            
            # 视频写入器参数
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(video_path, fourcc, export_fps, (width, height))
            
            # 写入视频帧
            for frame_num in range(start_frame, min(end_frame + 1, len(self.processed_frames))):
                # 将RGB转换回BGR
                frame_bgr = cv2.cvtColor(self.processed_frames[frame_num], cv2.COLOR_RGB2BGR)
                out.write(frame_bgr)
                    
            out.release()
            
            # 创建标签文件
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(tag_text)
            
    messagebox.showinfo("完成", f"已导出 {len(self.tags)} 个标记片段到: {main_folder}")

# Note: This was originally a method of class VideoTagger
# You may need to adjust the implementation based on class context
__all__ = ['export_tags']