import os
from PIL import Image
from tkinter import filedialog, Tk
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_images_to_png(input_folder):
    """
    将指定文件夹中的所有支持格式的图片转换为PNG格式
    
    Args:
        input_folder (str): 包含图片文件的文件夹路径
    """
    # 支持的输入格式
    supported_formats = ('.jpg', '.jpeg', '.bmp', '.tiff', '.webp')
    
    # 创建输出文件夹
    output_folder = os.path.join(input_folder, "png_converted")
    os.makedirs(output_folder, exist_ok=True)
    
    # 获取所有支持的图片文件
    image_files = []
    for file in os.listdir(input_folder):
        if file.lower().endswith(supported_formats):
            image_files.append(os.path.join(input_folder, file))
    
    if not image_files:
        logger.info("未找到支持的图片文件")
        return
    
    logger.info(f"找到 {len(image_files)} 个图片文件")
    
    # 转换每个图片文件为PNG格式
    for image_path in image_files:
        try:
            # 打开图片
            with Image.open(image_path) as img:
                # 转换为RGB模式（如果需要）
                if img.mode in ('RGBA', 'LA', 'P'):
                    # 如果图片有透明通道，保持透明度
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    # 为RGBA图片创建白色背景
                    if img.mode == 'RGBA':
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1] if len(img.split()) == 4 else None)
                        img = background
                else:
                    img = img.convert('RGB')
                
                # 生成输出文件路径
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_path = os.path.join(output_folder, f"{base_name}.png")
                
                # 保存为PNG格式
                img.save(output_path, "PNG")
                logger.info(f"已转换: {os.path.basename(image_path)} -> {base_name}.png")
                
        except Exception as e:
            logger.error(f"转换图片 {image_path} 时出错: {e}")

def select_folder():
    """选择包含图片文件的文件夹"""
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    folder = filedialog.askdirectory(title="选择包含图片文件的文件夹")
    root.destroy()
    return folder

def main():
    """主函数"""
    print("图片格式转换工具 (转换为PNG)")
    print("=" * 30)
    
    # 选择输入文件夹
    input_folder = select_folder()
    if not input_folder:
        print("未选择文件夹，程序退出")
        return
    
    print(f"选择的文件夹: {input_folder}")
    
    # 转换图片格式
    convert_images_to_png(input_folder)
    
    print("图片格式转换完成!")

if __name__ == "__main__":
    main()