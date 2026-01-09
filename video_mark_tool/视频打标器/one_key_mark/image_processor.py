import os
import json
from PIL import Image
from ai_processor import AIProcessor
import logging

logger = logging.getLogger(__name__)

class ImageProcessor:
    def __init__(self, config_manager):
        self.config = config_manager
        self.ai_processor = AIProcessor(config_manager)
        # 支持的图片格式
        self.supported_image_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
    
    def get_image_files(self, folder):
        """获取文件夹中所有图片文件"""
        image_files = []
        for file in os.listdir(folder):
            if file.lower().endswith(self.supported_image_formats):
                image_files.append(os.path.join(folder, file))
        return image_files

    def process_image(self, image_path, common_output_dir=None):
        """处理单个图片文件"""
        logger.info(f"开始处理图片: {image_path}")
        print(f"开始处理图片: {os.path.basename(image_path)}")
        
        # 如果提供了公共输出目录，则使用它；否则创建专门的文件夹
        if common_output_dir:
            output_dir = common_output_dir
            os.makedirs(output_dir, exist_ok=True)
        else:
            image_name = os.path.splitext(os.path.basename(image_path))[0]
            output_dir = os.path.join(os.path.dirname(image_path), f"{image_name}_processed")#文件夹的名字
            os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 打开图片
            image = Image.open(image_path).convert('RGB')
            
            # 调整图片大小（如果太大）
            max_size = (1024, 1024)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # AI生成标签
            #print(f"  正在生成图片描述...")
            caption = self.ai_processor.generate_image_caption_with_ai(image)
            print(f"  图片描述: {caption[:1000]}...")
            
            # 保存处理后的图片
            # 保存在指定的文件夹中，格式改为PNG
            image_basename = os.path.splitext(os.path.basename(image_path))[0]
            output_image_path = os.path.join(output_dir, f"{image_basename}.png")
            image.save(output_image_path, "PNG")
            
            # 保存标签
            txt_output_path = os.path.join(output_dir, f"{image_basename}.txt")
            with open(txt_output_path, 'w', encoding='utf-8') as f:
                f.write(caption)
            
            # 保存元数据（现在无论是否使用公共目录都会创建元数据）
            # 移除了 if not common_output_dir 条件，使元数据始终被创建
            metadata = {
                "source_image": image_path,
                "processed_image": output_image_path,
                "caption": caption,
                "text_file": txt_output_path
            }
            
            metadata_path = os.path.join(output_dir, "metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"图片处理完成: {image_path}，生成描述: {caption}")
            #print(f"图片处理完成: {os.path.basename(image_path)}")
            
        except Exception as e:
            logger.error(f"处理图片 {image_path} 时出错: {e}")
            print(f"处理图片 {os.path.basename(image_path)} 时出错: {e}")

    def process_all_images(self, input_folder):
        """处理文件夹中的所有图片"""
        image_files = self.get_image_files(input_folder)
        
        if not image_files:
            logger.info("未找到支持的图片文件")
            return
            
        logger.info(f"找到 {len(image_files)} 个图片文件")
        print(f"找到 {len(image_files)} 个图片文件")
        
        # 创建一个统一的输出文件夹用于存放所有图片和标签
        common_output_dir = os.path.join(input_folder, "processed_images")
        os.makedirs(common_output_dir, exist_ok=True)
        
        for i, image_file in enumerate(image_files, 1):
            try:
                #print(f"[{i}/{len(image_files)}] 正在处理: {os.path.basename(image_file)}")
                self.process_image(image_file, common_output_dir)
                #print(f"[{i}/{len(image_files)}] 完成处理: {os.path.basename(image_file)}\n")
            except Exception as e:
                logger.error(f"处理图片 {image_file} 时出错: {e}")
                print(f"[{i}/{len(image_files)}] 处理失败: {os.path.basename(image_file)} - {e}")