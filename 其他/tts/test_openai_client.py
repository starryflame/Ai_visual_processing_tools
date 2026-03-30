"""
使用 openai-python SDK 调用本地 TTS 服务的示例
需要先安装：pip install openai fastapi uvicorn gradio-client
"""
from openai import OpenAI
import os

# 配置本地服务地址（假设服务器运行在 http://localhost:8000）
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # 本地服务不需要 API Key
)


def generate_tts_openai():
    """使用 OpenAI SDK 风格调用 TTS"""
    
    response = client.audio.speech.create(
        model="tts-0.6B",
        input="这是一个功能丰富的 AI 视觉处理工具集合，包括图片和视频的标注、标签管理、批处理和 AI 视频生成功能。",
        voice="alloy"  # alloy, echo, fable, onyx, nova, shimmer
    )
    
    # 保存音频文件
    audio_file_path = "output.mp3"
    response.stream_to_file(audio_file_path)
    
    print(f"音频已保存到：{audio_file_path}")
    
    # 播放（使用系统默认播放器）
    os.system(f"start {audio_file_path}")


def generate_tts_wav():
    """生成 WAV 格式"""
    response = client.audio.speech.create(
        model="tts-0.6B",
        input="欢迎使用 OpenAI 兼容的 TTS 服务。",
        voice="echo",
        response_format="wav"
    )
    
    audio_file_path = "output.wav"
    with open(audio_file_path, "wb") as f:
        for chunk in response.iter_bytes():
            f.write(chunk)
    
    print(f"WAV 音频已保存到：{audio_file_path}")


def list_models():
    """列出可用的 TTS 模型"""
    models = client.models.list()
    for model in models.data:
        print(f"Model ID: {model.id}, Owned by: {model.owned_by}")


if __name__ == "__main__":
    # 先运行 tts_server.py 启动服务器：python tts_server.py
    
    print("=== 列出可用模型 ===")
    list_models()
    
    print("\n=== 生成 MP3 音频 ===")
    generate_tts_openai()
    
    print("\n=== 生成 WAV 音频 ===")
    generate_tts_wav()
