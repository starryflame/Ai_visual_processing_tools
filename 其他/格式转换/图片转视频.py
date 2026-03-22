import os
import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import numpy as np

def convert_images_to_video(input_folder, output_folder, status_label=None):
    """
    将文件夹中的所有图片转换为单帧 MP4 视频
    
    参数:
        input_folder: 输入图片文件夹路径
        output_folder: 输出视频文件夹路径
        status_label: 用于更新状态信息的 Label 组件（可选）
    """
    # 支持的图片格式
    supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    
    # 创建输出文件夹（如果不存在）
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # 获取所有图片文件
    image_files = []
    for file in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file)
        if os.path.isfile(file_path):
            ext = Path(file).suffix.lower()
            if ext in supported_formats:
                image_files.append(file)
    
    if not image_files:
        msg = f"在文件夹 '{input_folder}' 中未找到任何图片文件"
        print(msg)
        if status_label:
            status_label.config(text=msg)
        return
    
    print(f"找到 {len(image_files)} 张图片，开始转换...")
    
    # 转换每张图片为视频
    success_count = 0
    for image_file in image_files:
        try:
            # 构建输入和输出文件路径
            input_path = os.path.join(input_folder, image_file)
            
            # 生成输出文件名（保持原名，修改后缀为.mp4）
            name_without_ext = Path(image_file).stem
            output_file = f"{name_without_ext}.mp4"
            output_path = os.path.join(output_folder, output_file)
            
            # 【修改】使用 np.fromfile + cv2.imdecode 替代 cv2.imread 以支持中文路径
            img_array = np.fromfile(input_path, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                print(f"无法读取图片 (可能文件损坏或不支持): {image_file}")
                continue
            
            height, width = img.shape[:2]
            
            # 创建视频写入器
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 1  # 1 帧每秒
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                print(f"无法创建视频文件：{output_file}")
                continue
            
            # 写入单帧
            out.write(img)
            out.release()
            
            print(f"已转换：{image_file} -> {output_file}")
            success_count += 1
            
        except Exception as e:
            print(f"转换失败 {image_file}: {str(e)}")
    
    final_msg = f"转换完成！成功转换 {success_count}/{len(image_files)} 个文件"
    print(final_msg)
    if status_label:
        status_label.config(text=final_msg)
    if success_count > 0:
        messagebox.showinfo("完成", f"{final_msg}\n输出文件夹：{output_folder}")

def select_input_folder():
    folder = filedialog.askdirectory(title="选择输入图片文件夹")
    if folder:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, folder)

def select_output_folder():
    folder = filedialog.askdirectory(title="选择输出视频文件夹")
    if folder:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, folder)

def start_conversion():
    input_path = input_entry.get()
    output_path = output_entry.get()
    
    if not input_path or not output_path:
        messagebox.showwarning("警告", "请选择输入和输出文件夹")
        return
        
    if not os.path.exists(input_path):
        messagebox.showerror("错误", f"输入文件夹 '{input_path}' 不存在")
        return
    
    # 禁用按钮防止重复点击
    convert_btn.config(state=tk.DISABLED)
    status_label.config(text="正在转换...")
    
    # 在后台线程运行以避免界面卡死（简单起见这里直接调用，大文件可能卡顿，生产环境建议加 threading）
    try:
        convert_images_to_video(input_path, output_path, status_label)
    except Exception as e:
        messagebox.showerror("错误", f"转换过程中发生异常：{str(e)}")
    finally:
        convert_btn.config(state=tk.NORMAL)
        if "完成" not in status_label.cget("text"):
            status_label.config(text="就绪")

def create_ui():
    global input_entry, output_entry, convert_btn, status_label
    
    root = tk.Tk()
    root.title("图片转单帧视频工具")
    root.geometry("600x250")
    
    # 输入文件夹
    tk.Label(root, text="输入文件夹:").grid(row=0, column=0, padx=10, pady=10, sticky='e')
    input_entry = tk.Entry(root, width=50)
    input_entry.grid(row=0, column=1, padx=5)
    tk.Button(root, text="浏览...", command=select_input_folder).grid(row=0, column=2, padx=5)
    
    # 输出文件夹
    tk.Label(root, text="输出文件夹:").grid(row=1, column=0, padx=10, pady=10, sticky='e')
    output_entry = tk.Entry(root, width=50)
    output_entry.grid(row=1, column=1, padx=5)
    tk.Button(root, text="浏览...", command=select_output_folder).grid(row=1, column=2, padx=5)
    
    # 转换按钮
    convert_btn = tk.Button(root, text="开始转换", command=start_conversion, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
    convert_btn.grid(row=2, column=1, pady=20)
    
    # 状态栏
    status_label = tk.Label(root, text="就绪", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status_label.grid(row=3, column=0, columnspan=3, sticky='we', padx=5, pady=5)
    
    root.mainloop()

if __name__ == "__main__":
    create_ui()