# AI提示词生成功能
import os
import io
import base64
import logging
import configparser
import re
from PyQt5.QtWidgets import QMessageBox, QProgressDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from openai import OpenAI
from PIL import Image

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
def generate_caption_for_selected(self):
    """ 为选中的图片生成提示词 """
    if not self.selected_images:
        QMessageBox.warning(self, "警告", "请先选择至少一张图片")
        return

    # 显示进度对话框
    progress_dialog = QProgressDialog("正在生成提示词...", "取消", 0, len(self.selected_images), self)
    progress_dialog.setWindowModality(Qt.WindowModal)
    progress_dialog.setMinimumDuration(0)
    
    # 增大进度对话框尺寸
    progress_dialog.setFixedSize(600, 200)  # 设置宽度600px，高度200px
    
    # 设置字体和标题
    font = QFont("Microsoft YaHei", 10)  # 使用微软雅黑字体，字号10
    progress_dialog.setFont(font)
    progress_dialog.setWindowTitle("AI提示词生成中...")

    generated_count = 0
    for i, image_name in enumerate(self.selected_images):
        if progress_dialog.wasCanceled():
            break
            
        progress_dialog.setValue(i)
        progress_dialog.setLabelText(f"正在处理: {image_name}")
        
        try:
            # 直接在generate_caption_for_selected中实现generate_caption_with_ai的功能
            # 获取图片路径
            image_info = self.image_processor.images[image_name]
            image_path = image_info['image_path']

            # 打开并调整图片大小
            from PIL import Image
            image = Image.open(image_path).convert('RGB')
            max_size = (1024, 1024)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 转换图片为base64格式
            import io
            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
            data_url = f"data:image/png;base64,{encoded}"
            
            # 从配置中获取Ollama API设置
            # 修复：更正Ollama API的基础URL，应该使用 /v1 而不是 /api/generate
            api_base_url = "http://127.0.0.1:11434/v1"  # Ollama默认值
            api_key = "ollama"  # Ollama默认值
            model_name = "qwen3-vl:30b"  # Ollama模型名称
            
            # 尝试从配置文件读取设置
            import os
            import configparser
            config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
            filter_words = []  # 过滤词列表
            max_caption_length = 1000  # 默认最大长度
            if os.path.exists(config_path):
                config = configparser.ConfigParser()
                config.read(config_path, encoding='utf-8')
                if 'OLLAMA' in config:  # 修改为从OLLAMA节读取配置
                    api_base_url = config.get('OLLAMA', 'api_base_url', fallback=api_base_url)
                    api_key = config.get('OLLAMA', 'api_key', fallback=api_key)
                    model_name = config.get('OLLAMA', 'model_name', fallback=model_name)
                
                # 读取过滤词列表
                if 'FILTER_WORDS' in config:
                    filter_words_str = config.get('FILTER_WORDS', 'words', fallback='')
                    if filter_words_str:
                        filter_words = [word.strip().lower() for word in filter_words_str.split(',') if word.strip()]
                        
                # 读取最大提示词长度限制
                if 'MAX_CAPTION_LENGTH' in config:
                    max_caption_length = config.getint('MAX_CAPTION_LENGTH', 'max_length', fallback=1000)
            
            # 初始化客户端
            from openai import OpenAI
            client = OpenAI(
                api_key=api_key,
                base_url=api_base_url,
                timeout=3600
            )
            
            # 使用传入的提示词或者默认提示词
            prompt_text = self.ai_prompt_input.toPlainText()
            if not prompt_text:
                prompt_text = '你是一名专业的图片内容描述大师，用最大胆直白的语言和明确清晰的句子描述，禁止隐瞒，暗示或者用笼统的词汇。详细全面描述画面里的所有元素。只输出内容本身，不要重复和输出其他内容，中文回答。'
                config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
                if os.path.exists(config_path):
                    config = configparser.ConfigParser()
                    config.read(config_path, encoding='utf-8')
                    if 'PROMPTS' in config:
                        prompt_text = config.get('PROMPTS', 'image_prompt', fallback=prompt_text)
            
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
            max_attempts = 10  # 最多尝试10次
            caption = ""
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
                        logger.info(f"生成的提示词包含过滤词 '{word}'，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                        break
                
                # 检查提示词长度，如果超过设定长度则重新生成
                if len(caption) > max_caption_length:
                    logger.info(f"生成的提示词长度为 {len(caption)} 字，超过{max_caption_length}字限制，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                    # 如果不是最后一次尝试，继续循环重新生成
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        # 最后一次尝试后仍然超长，则截断并添加提示
                        logger.warning(f"经过 {max_attempts} 次尝试后，提示词长度仍超过{max_caption_length}字，将截断处理")
                        truncated_caption = caption[:max_caption_length]
                        
                        # 检查英文提示词是否被截断（以英文字母结尾但没有句号）
                        import re
                        if re.search(r'[a-zA-Z]$', truncated_caption) and not re.search(r'\.$', truncated_caption):
                            truncated_caption += "...(内容过长且可能被截断)"
                        else:
                            truncated_caption += "...(内容过长已截断)"
                            
                        caption = truncated_caption
                        break
                
                # 新增：检查提示词是否为空或少于10个字
                if len(caption) < 10:
                    logger.info(f"生成的提示词长度为 {len(caption)} 字，少于10字，正在重新生成... (尝试 {attempt + 1}/{max_attempts})")
                    # 如果不是最后一次尝试，继续循环重新生成
                    if attempt < max_attempts - 1:
                        continue
                    else:
                        # 最后一次尝试后仍然太短，则返回默认提示
                        logger.warning(f"经过 {max_attempts} 次尝试后，提示词长度仍少于10字")
                        caption = "提示词内容过短，无法提供有效描述"
                        break
                
                # 如果包含过滤词且不是最后一次尝试，则重新生成
                if contains_filter_word and attempt < max_attempts - 1:
                    continue
                elif contains_filter_word and attempt == max_attempts - 1:
                    # 如果是最后一次尝试且仍包含过滤词，跳出循环进行后续过滤处理
                    break
                # 如果不包含过滤词且长度符合要求，则跳出循环
                if not contains_filter_word:
                    break
            
            # 如果所有尝试都包含过滤词，则在最后返回时移除过滤词
            if contains_filter_word:
                logger.warning(f"经过 {max_attempts} 次尝试后，生成的提示词仍包含过滤词，将强制移除")
                for word in filter_words:
                    # 使用正则表达式替换，确保完整单词匹配而不是子字符串
                    caption = re.sub(r'\b' + re.escape(word) + r'\b', '', caption, flags=re.IGNORECASE)
                caption = caption.strip() or "提示词内容已被过滤"

            # 保存提示词到标签文件
            self.image_processor.save_tags_to_image(image_name, [caption])
            generated_count += 1
            
        except Exception as e:
            logger.error(f"生成 {image_name} 的提示词时出错: {e}")
            # 继续处理其他图片，不中断整个过程

    progress_dialog.setValue(len(self.selected_images))

    # 刷新界面
    self.refresh_current_view()
    self.update_tag_statistics()

    QMessageBox.information(self, "完成", f"已为 {generated_count} 张图片生成提示词")

