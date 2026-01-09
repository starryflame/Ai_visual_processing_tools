import os
import shutil
from pathlib import Path

def merge_resource_files():
    # 定义路径
    resource_dir = Path("resource")
    merged_dir = Path("merged")
    
    # 创建合并目录
    merged_dir.mkdir(exist_ok=True)
    
    # 支持的图片和视频格式
    media_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.mp4', '.avi', '.mov', '.mkv', '.wmv'}
    
    # 计数器用于重命名文件
    counter = 1
    
    # 创建文件映射，将相同名称的文件配对
    file_pairs = {}
    
    # 递归遍历resource目录下的所有文件
    for root, dirs, files in os.walk(resource_dir):
        for file in files:
            file_path = Path(root) / file
            file_stem = file_path.stem  # 文件名（不含扩展名）
            file_ext = file_path.suffix.lower()  # 扩展名
            
            # 为每个文件创建全局唯一的键值，避免不同目录下同名文件冲突
            unique_key = f"{file_stem}_{root.replace(str(resource_dir), '').replace(os.sep, '_')}"
            if unique_key not in file_pairs:
                file_pairs[unique_key] = {}
            
            if file_ext in media_extensions:
                file_pairs[unique_key]['media'] = file_path
            elif file_ext == '.txt':
                file_pairs[unique_key]['txt'] = file_path
    
    # 处理每个配对
    for unique_key, pair in file_pairs.items():
        if 'media' in pair and 'txt' in pair:
            media_path = pair['media']
            txt_path = pair['txt']
            
            # 构造新文件名
            media_ext = media_path.suffix
            new_media_name = f"{counter:06d}{media_ext}"  # 6位数字前导零
            new_txt_name = f"{counter:06d}.txt"
            
            # 修改: 将复制操作改为移动操作
            shutil.move(media_path, merged_dir / new_media_name)
            shutil.move(txt_path, merged_dir / new_txt_name)
            
            print(f"已处理: {unique_key} -> {new_media_name} 和 {new_txt_name}")
            counter += 1
        elif 'media' in pair:
            print(f"警告: 找到媒体文件 {pair['media']} 但没有对应的.txt文件")
        elif 'txt' in pair:
            print(f"警告: 找到.txt文件 {pair['txt']} 但没有对应的媒体文件")
    
    # 删除resource目录下的所有子目录，但保留resource目录本身
    for item in resource_dir.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
            print(f"已删除目录: {item}")

if __name__ == "__main__":
    merge_resource_files()
    print("文件合并完成！")