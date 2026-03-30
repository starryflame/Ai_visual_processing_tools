"""
TTS 适配器 - 将 OpenAI API 格式转换为本地 Gradio TTS 调用
"""
from gradio_client import Client
import os


class TTSAAdapter:
    """TTS 服务适配器"""
    
    def __init__(self, gradio_url: str = "http://localhost:7862/"):
        self.client = Client(gradio_url)
        self.gradio_url = gradio_url
    
    def generate_tts(
        self,
        text: str,
        voice: str = "少女音 1",
        speed: float = 1.0,
        temperature: float = 0.6,
        response_format: str = "wav"
    ) -> tuple:
        """
        生成语音
        
        Args:
            text: 要转换的文本
            voice: 音色 (少女音 1, 御姐，萝莉 1, 老男人等)
            speed: 语速 (0.5-2.0)
            temperature: 温度参数 (影响发音变化)
            response_format: 期望的输出格式
        
        Returns:
            tuple: (音频文件路径，元数据)
        """
        result = self.client.predict(
            voices_dropdown=voice,
            text=text,
            prompt_text="",
            prompt_audio=None,
            speed=speed,
            chunk_size=200,
            batch=25,
            lang="Auto",
            model_type="0.6B",
            temperature=temperature,
            auto_up=False,
            api_name="/do_job"
        )
        
        return result
    
    def get_voices(self) -> list:
        """获取可用的音色列表"""
        # 这里可以根据实际服务返回的选项来硬编码或动态获取
        return [
            "少女音 1",
            "御姐", 
            "萝莉 1",
            "老男人"
        ]


# 测试用
if __name__ == "__main__":
    adapter = TTSAAdapter()
    
    # 测试生成
    result = adapter.generate_tts(
        text="这是一个测试，欢迎使用 OpenAI 兼容的 TTS 服务。",
        voice="少女音 1",
        speed=1.0,
        temperature=0.6,
        response_format="wav"
    )
    
    print("生成结果:", result)
    
    if isinstance(result, tuple):
        audio_path = result[0]
    else:
        audio_path = result
    
    if os.path.exists(audio_path):
        import winsound
        winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        print(f"已播放音频：{audio_path}")
