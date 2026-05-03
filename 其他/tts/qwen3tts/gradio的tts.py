from gradio_client import Client
import winsound
import os

client = Client("http://localhost:7862/")

# 生成语音
result = client.predict(
    voices_dropdown="少女音 1",        # 音色：御姐、萝莉 1、老男人、少女音1...
    text="一个功能丰富的 AI 视觉处理工具集合，包括图片和视频的标注、标签管理、批处理和 AI 视频生成功能。",  # 机器人要说的话
    prompt_text="",               # 留空
    prompt_audio=None,            # 留空
    speed=1,                      # 语速
    chunk_size=900,               # 显存够用就不改
    batch=25,
    lang="Auto",                  # 自动识别语言
    model_type="1.7B",
    temperature=0.1,
    auto_up=False,
    api_name="/do_job"
)

# client.predict 返回元组 (path1, path2)，取第一个元素作为音频路径
audio_path = result[0] if isinstance(result, tuple) else result

print("生成的语音文件路径：", audio_path)

# 播放音频（仅支持 WAV 格式）
if os.path.exists(audio_path):
    winsound.PlaySound(audio_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    print("正在播放音频...")
else:
    print("未找到生成的音频文件，无法播放")
