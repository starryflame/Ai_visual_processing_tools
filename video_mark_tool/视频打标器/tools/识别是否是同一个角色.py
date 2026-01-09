import base64
import cv2
import os
import shutil
from openai import OpenAI
import configparser
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    # 假设配置文件在上级目录
    config_path = r"j:\Data\Ai_visual_processing_tools\video_mark_tool\视频打标器\config.ini"
    if os.path.exists(config_path):
        config.read(config_path)
    return config

def encode_image_to_base64(image_path):
    """将图片转换为base64格式"""
    try:
        # 使用opencv读取图片
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"无法读取图片: {image_path}")
            return None
        
        # 转换为RGB格式
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # 编码为PNG格式
        _, buffer = cv2.imencode(".png", image_rgb)
        encoded = base64.b64encode(buffer).decode("utf-8")
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logger.error(f"图片编码失败: {e}")
        return None

def check_same_person(reference_image_path, folder_path, prompt_text, output_folder):
    """
    检查文件夹中的图片是否与参考图片是同一个人
    
    Args:
        reference_image_path (str): 参考图片路径
        folder_path (str): 图片文件夹路径
        prompt_text (str): 提示词
        output_folder (str): 输出文件夹路径
    """
    
    # 加载配置
    config = load_config()
    
    # 创建输出文件夹
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # 获取API配置
    api_base_url = config.get('VLLM', 'api_base_url', fallback="http://127.0.0.1:8000/v1")
    api_key = config.get('VLLM', 'api_key', fallback="EMPTY")
    model_name = config.get('VLLM', 'model_name', fallback="/models/Qwen3-VL-8B-Instruct")
    
    # 初始化客户端
    client = OpenAI(
        api_key=api_key,
        base_url=api_base_url,
        timeout=3600
    )
    
    # 编码参考图片
    reference_image_data = encode_image_to_base64(reference_image_path)
    if not reference_image_data:
        logger.error("参考图片编码失败")
        return
    
    # 获取文件夹中的所有图片文件
    image_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    image_files = [f for f in os.listdir(folder_path) 
                   if f.lower().endswith(image_extensions)]
    
    logger.info(f"找到 {len(image_files)} 张图片待处理")
    
    same_person_count = 0
    
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        logger.info(f"处理图片: {image_file}")
        
        # 编码对比图片
        compare_image_data = encode_image_to_base64(image_path)
        if not compare_image_data:
            logger.warning(f"跳过无法编码的图片: {image_file}")
            continue
        
        # 构造消息内容
        content_list = [
            {
                "type": "text",
                "text": prompt_text
            },
            {
                "type": "image_url",
                "image_url": {"url": reference_image_data}
            },
            {
                "type": "image_url",
                "image_url": {"url": compare_image_data}
            }
        ]
        
        messages = [{"role": "user", "content": content_list}]
        
        try:
            # 发送请求到vLLM API
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=10,
                temperature=0.1,
                top_p=0.9,
            )
            
            result = response.choices[0].message.content.strip().lower()
            logger.info(f"{image_file} 的判断结果: {result}")
            
            # 如果模型判断是同一个人，则复制图片到输出文件夹
            if "是" in result and "不是" not in result:
                output_path = os.path.join(output_folder, image_file)
                shutil.copy2(image_path, output_path)
                same_person_count += 1
                logger.info(f"图片 {image_file} 已复制到输出文件夹")
            elif "不是" in result:
                logger.info(f"图片 {image_file} 不是同一人")
            else:
                logger.warning(f"模型返回了意外的结果: {result}")
                
        except Exception as e:
            logger.error(f"处理图片 {image_file} 时出错: {e}")
            continue
    
    logger.info(f"处理完成，共找到 {same_person_count} 张相同人物的图片")

if __name__ == "__main__":
    # 示例使用方法
    # 请根据实际情况修改以下路径和提示词
    
    # 参考图片路径
    reference_image_path = r"J:\path\to\reference\image.jpg"
    
    # 待比较的图片文件夹路径
    folder_path = r"J:\path\to\image\folder"
    
    # 输出文件夹路径
    output_folder = r"J:\path\to\output\folder"
    
    # 提示词，引导模型只回答"是"或"不是"
    prompt_text = "这两张图片中的人物是同一个人吗？请只回答‘是’或‘不是’。禁止输入其他内容。"
    
    # 执行检查
    check_same_person(reference_image_path, folder_path, prompt_text, output_folder)