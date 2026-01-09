import os
import configparser

class ConfigManager:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), r'J:\Data\Ai_visual_processing_tools\video_mark_tool\视频打标器\one_key_mark\config.ini')
            
        self.config = configparser.ConfigParser()
        if os.path.exists(config_path):
            # 使用 utf-8 编码读取配置文件，避免 UnicodeDecodeError 错误
            self.config.read(config_path, encoding='utf-8')
        else:
            self._create_default_config(config_path)
    
    def _create_default_config(self, config_path):
        """创建默认配置"""
        self.config['PROCESSING'] = {
            'target_frame_rate': '24',
            'target_frame_height': '720',
            'segment_duration': '5',
            'max_sample_frames': '64',
            'max_filename_length': '50'
        }
        
        self.config['MODEL'] = {
            'qwen_vl_model_path': r'J:\models\LLM\Qwen-VL\Qwen3-VL-8B-Instruct',
            'torch_dtype': 'fp32',
            'max_new_tokens': '1024',
            'temperature': '0.6',
            'top_p': '0.9'
        }
        
        self.config['VLLM'] = {
            'api_base_url': 'http://127.0.0.1:8000/v1',
            'api_key': 'EMPTY',
            'model_name': '/models/Qwen3-VL-8B-Instruct',
            'max_tokens': '1024',
            'temperature': '0.3',
            'top_p': '0.9'
        }
        
        # 添加提示词配置
        self.config['PROMPTS'] = {
            'video_prompt': '以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。',
            'image_prompt': '以提示词格式详细描述画面。请用中文回答，尽量详细、连贯。只输出提示词本身，不要输出其他内容。'
        }
        
        # 添加过滤词配置
        self.config['FILTER'] = {
            'keywords': '无关,无法,抱歉,对不起,不知道,不清楚,不相关,重复,无意义,胡言乱语,乱码,废话'
        }
    
        # 在创建默认配置文件时也使用 utf-8 编码
        with open(config_path, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
    
    def get(self, section, key, fallback=None):
        return self.config.get(section, key, fallback=fallback)
    
    def getint(self, section, key, fallback=None):
        return self.config.getint(section, key, fallback=fallback)
    
    def getfloat(self, section, key, fallback=None):
        return self.config.getfloat(section, key, fallback=fallback)
    
    def getboolean(self, section, key, fallback=None):
        return self.config.getboolean(section, key, fallback=fallback)