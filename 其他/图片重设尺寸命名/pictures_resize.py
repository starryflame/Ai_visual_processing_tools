import os
from PIL import Image
import math
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import sys

def process_single_image(args):
    """处理单张图片的函数"""
    file_path, supported_formats, output_folder, resource_folder, index = args
    
    try:
        filename = os.path.basename(file_path)
        
        # 打开图片
        with Image.open(file_path) as img:
            width, height = img.size
            
            # 计算长宽比
            aspect_ratio = max(width, height) / min(width, height)
            
            # 过滤长宽比悬殊的图片(长宽比大于3:1)
            if aspect_ratio > 3.0:
                return f"跳过 {file_path} - 长宽比悬殊 ({aspect_ratio:.2f}:1)"
            
            # 如果图片的长边小于等于1280，则不调整
            if max(width, height) <= 1280:
                new_width, new_height = width, height
            else:
                # 计算缩放比例，使长边变为1280
                if width > height:
                    new_width = 1280
                    new_height = int(height * (1280 / width))
                else:
                    new_height = 1280
                    new_width = int(width * (1280 / height))
            
            # 调整图片大小
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 生成新的文件名（改为png格式）- 使用序号命名
            new_filename = f"{index}_picture.png"
            
            # 直接保存到输出文件夹，不保持目录结构
            output_path = os.path.join(output_folder, new_filename)
            
            # 保存为PNG格式
            resized_img.save(output_path, 'PNG')
            return f"已处理: {file_path} -> {output_path} ({new_width}x{new_height})"
    
    except Exception as e:
        return f"处理 {file_path} 时出错: {e}"

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

def resize_images_in_folder():
    # 创建输出文件夹
    output_folder = "resized_images"
    os.makedirs(output_folder, exist_ok=True)
    
    # 支持的图片格式
    supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    
    # 遍历resource文件夹中的所有文件和子目录
    resource_folder = get_resource_path("resource")
    if not os.path.exists(resource_folder):
        print(f"错误: {resource_folder} 文件夹不存在")
        return
    
    # 收集所有需要处理的图片文件
    image_files = []
    index = 1
    for root, dirs, files in os.walk(resource_folder):
        for filename in files:
            if filename.lower().endswith(supported_formats):
                file_path = os.path.join(root, filename)
                image_files.append((file_path, supported_formats, output_folder, resource_folder, index))
                index += 1
    
    # 使用多进程处理图片
    cpu_count = multiprocessing.cpu_count()
    print(f"使用 {cpu_count} 个进程进行图片处理...")
    
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        # 提交所有任务
        future_to_file = {executor.submit(process_single_image, args): args[0] for args in image_files}
        
        # 处理完成的任务
        for future in as_completed(future_to_file):
            result = future.result()
            print(result)

if __name__ == "__main__":
    # 直接运行图片处理功能
    resize_images_in_folder()
    print("图片处理完成！")