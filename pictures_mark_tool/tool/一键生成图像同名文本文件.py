import os
from pathlib import Path

def generate_txt_files(folder_path, text_content):
    """
    为指定文件夹内的所有图片生成同名的txt文件
    
    Args:
        folder_path (str): 文件夹路径
        text_content (str): 要写入txt文件的内容
    """
    # 支持的图片格式
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}
    
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"错误：文件夹 '{folder_path}' 不存在")
        return
    
    if not os.path.isdir(folder_path):
        print(f"错误：'{folder_path}' 不是一个有效的文件夹")
        return
    
    # 遍历文件夹中的所有文件
    processed_count = 0
    for filename in os.listdir(folder_path):
        # 获取文件扩展名并转为小写
        file_extension = Path(filename).suffix.lower()
        
        # 如果是图片文件，则创建同名txt文件
        if file_extension in image_extensions:
            # 构建txt文件名
            txt_filename = Path(filename).stem + '.txt'
            txt_filepath = os.path.join(folder_path, txt_filename)
            
            # 写入文本内容到txt文件
            try:
                with open(txt_filepath, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                print(f"已创建: {txt_filename}")
                processed_count += 1
            except Exception as e:
                print(f"创建 {txt_filename} 时出错: {e}")
    
    print(f"\n处理完成！共创建了 {processed_count} 个txt文件。")

if __name__ == "__main__":
    # 获取用户输入
    folder_path = input("请输入文件夹路径: ").strip()
    text_content = input("请输入要写入txt文件的内容: ").strip()
    
    # 处理输入的文件夹路径（去除可能存在的引号）
    folder_path = folder_path.strip('"').strip("'")
    
    # 生成txt文件
    generate_txt_files(folder_path, text_content)