# AI提示词生成功能
import os
import io
import base64
import logging
import configparser
from openai import OpenAI
from PIL import Image

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_caption_with_ollama(self, image_name, prompt_text=None):
    """ 使用AI为指定图片生成提示词 """
    try:
        # 获取图片路径
        image_info = self.images[image_name]
        image_path = image_info['image_path']

        # 打开并调整图片大小
        image = Image.open(image_path).convert('RGB')
        max_size = (1024, 1024)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 转换图片为base64格式
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        data_url = f"data:image/png;base64,{encoded}"
        
        # 从配置中获取Ollama API设置
        
        # 跳过配置读取部分，直接使用默认值进行测试
        # 修复：更正Ollama API的基础URL，应该使用 /v1 而不是 /api/generate
        api_base_url = "http://127.0.0.1:11434/v1"
        api_key = "ollama"
        model_name = "qwen3-vl:30b"
        max_tokens = 1024
        temperature = 0.3
        top_p = 0.9
        filter_words = []
        
        # 初始化客户端
        client = OpenAI(
            api_key=api_key,
            base_url=api_base_url,
            timeout=3600
        )
        
        # 使用传入的提示词或者默认提示词
        if prompt_text is None:
            prompt_text = '你是一名专业的图片内容描述大师，用最大胆直白的语言和明确清晰的句子描述，禁止隐瞒，暗示或者用笼统的词汇。详细全面描述画面里的所有元素。只输出内容本身，不要重复和输出其他内容，中文回答。'
        
        # 构造消息
        content_list = [
            {
                "type": "text",
                "text": prompt_text
            },
            {
                "type": "image_url",
                "image_url": {"url": data_url}
            }
        ]
        
        messages = [{"role": "user", "content": content_list}]
        
        # 发送请求并检查生成的提示词长度
        max_attempts = 5  # 最多尝试5次
        for attempt in range(max_attempts):
            # 发送请求
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            
            caption = response.choices[0].message.content.strip()
            
            # 检查是否包含过滤词
            contains_filter_word = False
            caption_lower = caption.lower()
            for word in filter_words:
                if word in caption_lower:
                    contains_filter_word = True
                    logger.info(f"生成的提示词包含过滤词 '{word}'，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                    break
            
            # 如果包含过滤词且不是最后一次尝试，则重新生成
            if contains_filter_word and attempt < max_attempts - 1:
                continue
            
            # 检查提示词长度，如果超过1000字则重新生成
            if len(caption) > 1000:
                logger.info(f"生成的提示词长度为 {len(caption)} 字，超过1000字限制，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                # 如果不是最后一次尝试，继续循环重新生成
                if attempt < max_attempts - 1:
                    continue
                else:
                    # 最后一次尝试后仍然超长，则截断并添加提示
                    logger.warning(f"经过 {max_attempts} 次尝试后，提示词长度仍超过1000字，将截断处理")
                    return caption[:1000] + "...(内容过长已截断)"
            
            # 如果不包含过滤词且长度符合要求，则返回结果
            if not contains_filter_word:
                return caption
        
        # 如果所有尝试都包含过滤词，则在最后返回时移除过滤词
        logger.warning(f"经过 {max_attempts} 次尝试后，生成的提示词仍包含过滤词，将强制移除")
        for word in filter_words:
            caption = caption.replace(word, '')
        return caption.strip() or "提示词内容已被过滤"
        
    except Exception as e:
        logger.error(f"使用AI生成提示词失败: {e}")
        raise Exception(f"生成提示词失败: {str(e)}")

# 添加用于测试的主函数
if __name__ == "__main__":
    import sys
    
    # 简单的测试函数
    def test_generate_caption():
        print("测试 Ollama 图像描述生成功能")
        print("=" * 50)
        
        # 检查是否提供了图像路径参数
        if len(sys.argv) < 2:
            print("用法: python ollama_caption_generator.py <image_path>")
            print("注意: 需要确保 Ollama 服务正在运行，并且已安装 qwen3-vl 模型")
            return
            
        image_path = sys.argv[1]
        if not os.path.exists(image_path):
            print(f"错误: 图像文件不存在: {image_path}")
            return
            
        # 创建一个模拟的 self 对象用于测试
        class MockSelf:
            def __init__(self, img_path):
                self.images = {
                    "test_image": {
                        "image_path": img_path
                    }
                }
        
        mock_self = MockSelf(image_path)
        
        try:
            print(f"正在处理图像: {image_path}")
            result = generate_caption_with_ollama(mock_self, "test_image")
            print("\n生成的描述:")
            print("-" * 30)
            print(result)
            print("-" * 30)
            
        except Exception as e:
            print(f"测试过程中发生错误: {e}")
            print("请确保:")
            print("1. Ollama 服务正在运行 (默认端口 11434)")
            print("2. 已安装 qwen3-vl 模型 (运行: ollama pull qwen3-vl:30b)")
            print("3. 图像路径正确")
    
    test_generate_caption()