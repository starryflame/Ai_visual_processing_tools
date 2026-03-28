import os
import argparse
import re

def remove_suffix_from_filename(filename):
    """
    识别并删除文件名中的特定后缀（例如 _real, _fake 等）。
    根据需求示例：illust_..._real.png -> illust_....png
    逻辑：找到最后一个下划线后的部分，如果是特定后缀则删除。
    这里主要针对 '_real' 进行删除，如果需要扩展其他后缀可在此处添加。
    """
    name, ext = os.path.splitext(filename)
    
    # 定义需要删除的后缀列表，可根据需求扩展
    target_suffixes = ['_real', '_fake', '_hd', '_sd'] 
    
    # 检查文件名末尾是否包含这些后缀
    for suffix in target_suffixes:
        if name.endswith(suffix):
            new_name = name[:-len(suffix)] + ext
            return new_name
    
    # 如果没有匹配到特定后缀，返回原文件名（不做修改）
    return filename

def process_folder(folder_path):
    if not os.path.isdir(folder_path):
        print(f"错误：路径 '{folder_path}' 不是一个有效的文件夹。")
        return

    files = os.listdir(folder_path)
    count = 0
    
    print(f"开始处理文件夹：{folder_path}")
    
    for filename in files:
        # 跳过子目录，只处理文件
        if os.path.isdir(os.path.join(folder_path, filename)):
            continue
            
        new_filename = remove_suffix_from_filename(filename)
        
        if new_filename != filename:
            old_path = os.path.join(folder_path, filename)
            new_path = os.path.join(folder_path, new_filename)
            
            # 检查新文件名是否已存在，避免覆盖
            if os.path.exists(new_path):
                print(f"跳过：目标文件已存在 '{new_filename}'，源文件 '{filename}' 未修改。")
                continue
            
            try:
                os.rename(old_path, new_path)
                print(f"重命名成功：'{filename}' -> '{new_filename}'")
                count += 1
            except Exception as e:
                print(f"重命名失败：'{filename}'，错误信息：{e}")
        else:
            # 调试用，可选关闭
            # print(f"无需修改：'{filename}'")
            pass

    print(f"处理完成，共修改 {count} 个文件。")

if __name__ == "__main__":
    folder_path = input("请输入要处理的文件夹路径：").strip()
    
    if not folder_path:
        print("错误：路径不能为空。")
    else:
        process_folder(folder_path)