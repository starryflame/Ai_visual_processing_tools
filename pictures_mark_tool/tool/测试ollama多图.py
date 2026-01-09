import cv2
import os
import io
import base64
import logging
import configparser
from PIL import Image
from openai import OpenAI

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_frames_from_video(video_path, max_frames=16):
    """
    从视频中等间隔抽取帧
    
    Args:
        video_path (str): 视频文件路径
        max_frames (int): 最大抽帧数量，默认16帧
    
    Returns:
        list: 包含PIL Image对象的列表
    """
    frames = []
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise Exception("无法打开视频文件")
    
    # 获取视频总帧数
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    logger.info(f"视频信息: 总帧数={total_frames}, FPS={fps}")
    
    # 计算抽帧间隔
    interval = max(1, total_frames // max_frames)
    
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # 等间隔抽帧
        if frame_count % interval == 0 and extracted_count < max_frames:
            # 转换BGR到RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # 转换为PIL Image
            pil_image = Image.fromarray(rgb_frame)
            frames.append(pil_image)
            extracted_count += 1
            
        frame_count += 1
    
    cap.release()
    logger.info(f"成功抽取 {len(frames)} 帧")
    return frames

def convert_image_to_base64(image):
    """
    将PIL图像转换为base64编码
    
    Args:
        image (PIL.Image): 图像对象
    
    Returns:
        str: base64编码的图像数据URL
    """
    # 调整图片大小
    max_size = (1024, 1024)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # 转换图片为base64格式
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
    data_url = f"data:image/png;base64,{encoded}"
    
    return data_url

def generate_caption_with_ai_for_frames(frames, prompt_text=None):
    """
    使用AI为多个帧生成统一描述
    
    Args:
        frames (list): PIL Image对象列表
        prompt_text (str): 提示词
    
    Returns:
        str: AI生成的描述
    """
    try:
        # 转换所有帧为base64
        image_data_urls = [convert_image_to_base64(frame) for frame in frames]
        
        # 从配置中获取Ollama API设置
        api_base_url = "http://127.0.0.1:11434/v1"  # Ollama默认值
        api_key = "ollama"  # Ollama默认值
        model_name = "qwen3-vl:30b"  # Ollama模型名称
        
        # 尝试从配置文件读取设置
        config_path = os.path.join(os.path.dirname(__file__), '..', 'code', 'config.ini')
        filter_words = []  # 过滤词列表
        if os.path.exists(config_path):
            config = configparser.ConfigParser()
            config.read(config_path, encoding='utf-8')
            if 'OLLAMA' in config:
                api_base_url = config.get('OLLAMA', 'api_base_url', fallback=api_base_url)
                api_key = config.get('OLLAMA', 'api_key', fallback=api_key)
                model_name = config.get('OLLAMA', 'model_name', fallback=model_name)
            
            # 读取过滤词列表
            if 'FILTER_WORDS' in config:
                filter_words_str = config.get('FILTER_WORDS', 'words', fallback='')
                if filter_words_str:
                    filter_words = [word.strip().lower() for word in filter_words_str.split(',') if word.strip()]
        
        # 初始化客户端
        client = OpenAI(
            api_key=api_key,
            base_url=api_base_url,
            timeout=3600
        )
        
        # 使用传入的提示词或者默认提示词
        if prompt_text is None:
            prompt_text = '你是一名专业的图片内容描述大师，请放心使用最大胆直白的语言和明确清晰的句子描述，禁止隐瞒，暗示或者用笼统和词义不单一的词汇。详细全面描述画面里的所有元素。只输出内容本身，不要重复和输出其他内容，中文回答。'
            config_path = os.path.join(os.path.dirname(__file__), '..', 'code', 'config.ini')
            if os.path.exists(config_path):
                config = configparser.ConfigParser()
                config.read(config_path, encoding='utf-8')
                if 'PROMPTS' in config:
                    prompt_text = config.get('PROMPTS', 'image_prompt', fallback=prompt_text)
        
        # 构造消息内容
        content_list = [
            {
                "type": "text",
                "text": prompt_text
            }
        ]
        
        # 添加所有图片
        for data_url in image_data_urls:
            content_list.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
        
        messages = [{"role": "user", "content": content_list}]

        # 发送请求并检查生成的提示词长度
        max_attempts = 10  # 最多尝试10次
        for attempt in range(max_attempts):
            # 发送请求
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=1024,
                temperature=0.3,
                top_p=0.9,
            )
            
            caption = response.choices[0].message.content.strip()
            
            # 检查是否包含过滤词
            contains_filter_word = False
            caption_lower = caption.lower()
            for word in filter_words:
                if word in caption_lower:
                    contains_filter_word = True
                    logger.info(f"生成的描述包含过滤词 '{word}'，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                    break
            
            # 如果包含过滤词且不是最后一次尝试，则重新生成
            if contains_filter_word and attempt < max_attempts - 1:
                continue
            
            # 检查描述长度，如果超过1000字则重新生成
            if len(caption) > 1000:
                logger.info(f"生成的描述长度为 {len(caption)} 字，超过1000字限制，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                # 如果不是最后一次尝试，继续循环重新生成
                if attempt < max_attempts - 1:
                    continue
                else:
                    # 最后一次尝试后仍然超长，则截断并添加提示
                    logger.warning(f"经过 {max_attempts} 次尝试后，描述长度仍超过1000字，将截断处理")
                    return caption[:1000] + "...(内容过长已截断)"
            
            # 检查描述是否为空或少于10个字
            if len(caption) < 10:
                logger.info(f"生成的描述长度为 {len(caption)} 字，少于10字，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                # 如果不是最后一次尝试，继续循环重新生成
                if attempt < max_attempts - 1:
                    continue
                else:
                    # 最后一次尝试后仍然太短，则返回默认提示
                    logger.warning(f"经过 {max_attempts} 次尝试后，描述长度仍少于10字")
                    return "视频描述内容过短，无法提供有效描述"
            
            # 如果不包含过滤词且长度符合要求，则返回结果
            if not contains_filter_word:
                return caption
        
        # 如果所有尝试都包含过滤词，则在最后返回时移除过滤词
        logger.warning(f"经过 {max_attempts} 次尝试后，生成的描述仍包含过滤词，将强制移除")
        for word in filter_words:
            caption = caption.replace(word, '')
        return caption.strip() or "视频描述内容已被过滤"
        
    except Exception as e:
        logger.error(f"使用AI生成视频描述失败: {e}")
        raise Exception(f"生成视频描述失败: {str(e)}")

# 使用示例
if __name__ == "__main__":
    # 示例用法
    video_path = r"E:\Videos\split_videos\split_videos\115283-480p_part05.mp4"
    frames = extract_frames_from_video(video_path,16)
    description = generate_caption_with_ai_for_frames(frames)
    print(description)
    pass