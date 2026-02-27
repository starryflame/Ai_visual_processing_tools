import os
import tkinter as tk
from tkinter import filedialog
import datetime

def extract_txt_files():
    # 获取用户选择的源文件夹
    source_folder = filedialog.askdirectory(title="选择包含txt文件的文件夹")
    if not source_folder:
        return

    # 获取用户选择的目标文件夹
    target_folder = filedialog.askdirectory(title="选择保存提取内容的文件夹")
    if not target_folder:
        return

    # 创建目标文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_file = os.path.join(target_folder, f"extracted_content_{timestamp}.txt")

    try:
        with open(target_file, 'w', encoding='utf-8') as output_file:
            # 遍历源文件夹及其子文件夹
            for root, dirs, files in os.walk(source_folder):
                for file in files:
                    if file.endswith('.txt'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as input_file:
                                content = input_file.read()
                                output_file.write(content)
                                output_file.write("\n\n")
                        except Exception as e:
                            print(f"无法读取文件 {file_path}: {str(e)}")

        print(f"已成功提取所有txt文件内容到 {target_file}")
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")

# 运行提取函数
extract_txt_files()