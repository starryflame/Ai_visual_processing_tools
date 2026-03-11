import tkinter as tk
from tkinter import filedialog
import os


def convert_txt_files(folder_path):
    """
    将文件夹内所有 txt 文件中的中文逗号改为英文逗号，并删除所有空格
    """
    # 获取文件夹内所有 txt 文件
    txt_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]
    
    if not txt_files:
        print("该文件夹内没有 txt 文件")
        return
    
    for filename in txt_files:
        file_path = os.path.join(folder_path, filename)
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 替换中文逗号为英文逗号
            content = content.replace('，', ',')
            
            # 删除所有空格
            content = content.replace(' ', '')
            
            # 写入原文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"已处理：{filename}")
        except Exception as e:
            print(f"处理文件 {filename} 时出错：{e}")
    
    print(f"\n处理完成！共处理 {len(txt_files)} 个文件")


def select_folder():
    """
    弹出文件夹选择对话框
    """
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    folder_path = filedialog.askdirectory(title="请选择包含 txt 文件的文件夹")
    
    if folder_path:
        print(f"选中文件夹：{folder_path}")
        convert_txt_files(folder_path)
    else:
        print("未选择文件夹")
    
    root.destroy()


if __name__ == "__main__":
    select_folder()