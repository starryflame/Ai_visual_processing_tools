import os
import shutil
from pathlib import Path
import random

def split_large_folder(source_folder, max_files_per_folder=1000):
    """
    将大文件夹拆分成多个小文件夹
    
    Args:
        source_folder (str): 源文件夹路径
        max_files_per_folder (int): 每个小文件夹最大文件数
    """
    source_path = Path(source_folder)
    
    if not source_path.exists():
        print(f"源文件夹 {source_folder} 不存在")
        return
    
    # 获取所有文件（不包括子文件夹）
    files = [f for f in source_path.iterdir() if f.is_file()]
    
    if not files:
        print("源文件夹中没有文件")
        return
    
    folder_count = 0
    file_count = 0
    
    current_subfolder = None
    
    for file_path in files:
        # 当达到每个文件夹的最大文件数时，创建新文件夹
        if file_count % max_files_per_folder == 0:
            folder_count += 1
            subfolder_name = f"{source_path.name}_part_{folder_count}"
            # 修改：将part文件夹创建在源文件夹内而不是上级目录
            current_subfolder = source_path / subfolder_name
            current_subfolder.mkdir(exist_ok=True)
            print(f"创建文件夹: {current_subfolder}")
        
        # 移动文件到子文件夹
        destination = current_subfolder / file_path.name
        shutil.move(str(file_path), str(destination))
        file_count += 1
        
        if file_count % 100 == 0:
            print(f"已处理 {file_count} 个文件")
    
    print(f"拆分完成，共创建 {folder_count} 个子文件夹，处理 {file_count} 个文件")

def flatten_folder_structure(source_folder):
    """
    将文件夹结构扁平化，将所有子文件夹中的文件移动到根目录
    
    Args:
        source_folder (str): 源文件夹路径
    """
    source_path = Path(source_folder)
    
    if not source_path.exists():
        print(f"源文件夹 {source_folder} 不存在")
        return
    
    # 收集所有文件（包括子文件夹中的文件）
    all_files = []
    for root, dirs, files in os.walk(source_path):
        for file in files:
            file_path = Path(root) / file
            # 只收集非根目录下的文件
            if file_path.parent != source_path:
                all_files.append(file_path)
    
    moved_count = 0
    for file_path in all_files:
        destination = source_path / file_path.name
        
        # 如果目标文件已存在，添加序号
        counter = 1
        original_destination = destination
        while destination.exists():
            name_without_ext = original_destination.stem
            ext = original_destination.suffix
            destination = source_path / f"{name_without_ext}_{counter}{ext}"
            counter += 1
        
        shutil.move(str(file_path), str(destination))
        moved_count += 1
        
        if moved_count % 100 == 0:
            print(f"已移动 {moved_count} 个文件")
    
    # 删除空的子文件夹
    for item in source_path.iterdir():
        if item.is_dir():
            try:
                item.rmdir()  # 只能删除空文件夹
                print(f"删除空文件夹: {item}")
            except OSError:
                print(f"无法删除非空文件夹: {item}，请手动检查")
    
    print(f"扁平化完成，共移动 {moved_count} 个文件")

# 添加新功能：打乱文件夹中图片文件的名称顺序
def shuffle_image_names(source_folder):
    """
    将文件夹中的所有图片文件名称打乱
    
    Args:
        source_folder (str): 源文件夹路径
    """
    source_path = Path(source_folder)
    
    if not source_path.exists():
        print(f"源文件夹 {source_folder} 不存在")
        return
    
    # 定义常见的图片扩展名
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.svg'}
    
    # 获取所有图片文件
    image_files = [f for f in source_path.iterdir() 
                   if f.is_file() and f.suffix.lower() in image_extensions]
    
    if not image_files:
        print("源文件夹中没有图片文件")
        return
    
    # 创建临时名称以避免冲突
    temp_names = []
    final_names = [f.name for f in image_files]
    
    # 生成临时名称
    for i, img_file in enumerate(image_files):
        temp_name = f"temp_{i:06d}{img_file.suffix}"  # 使用固定宽度数字确保排序一致
        temp_names.append(temp_name)
    
    # 先将所有文件重命名为临时名称
    for img_file, temp_name in zip(image_files, temp_names):
        temp_path = source_path / temp_name
        img_file.rename(temp_path)
    
    # 打乱最终名称列表
    random.shuffle(final_names)
    
    # 再将文件重命名为打乱后的名称
    for temp_name, final_name in zip(temp_names, final_names):
        temp_path = source_path / temp_name
        final_path = source_path / final_name
        temp_path.rename(final_path)
    
    print(f"已完成 {len(image_files)} 个图片文件的名称打乱")

def main():
    """
    主函数 - 提供用户交互界面
    """
    print("大文件夹处理工具")
    print("1. 拆分大文件夹")
    print("2. 扁平化文件夹结构")
    # 添加新选项
    print("3. 打乱文件夹中图片文件名称顺序")
    
    choice = input("请选择操作 (1、2 或 3): ").strip()
    
    if choice == "1":
        folder_path = input("请输入要拆分的文件夹路径: ").strip()
        try:
            max_files = int(input("请输入每个子文件夹最大文件数 (默认1000): ") or "1000")
            split_large_folder(folder_path, max_files)
        except ValueError:
            print("输入的文件数量无效，使用默认值1000")
            split_large_folder(folder_path)
            
    elif choice == "2":
        folder_path = input("请输入要扁平化的文件夹路径: ").strip()
        flatten_folder_structure(folder_path)
        
    # 添加新功能选项的处理
    elif choice == "3":
        folder_path = input("请输入包含图片文件的文件夹路径: ").strip()
        shuffle_image_names(folder_path)
        
    else:
        print("无效的选择")

if __name__ == "__main__":
    main()