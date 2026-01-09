import time
from openai import OpenAI

client = OpenAI(
    api_key="EMPTY",
    base_url="http://127.0.0.1:8000/v1",
    timeout=3600
)

messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "video_url",
                "video_url": {
                    "url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen2-VL/space_woaudio.mp4"
                }
            },
            {
                "type": "text",
                "text": "简短描述视频内容"
            }
        ]
    }
]

start = time.time()

# When vLLM is launched with `--media-io-kwargs '{"video": {"num_frames": -1}}'`,
# video frame sampling can be configured via `extra_body` (e.g., by setting `fps`).
# This feature is currently supported only in vLLM.
#
# By default, `fps=2` and `do_sample_frames=True`.
# With `do_sample_frames=True`, you can customize the `fps` value to set your desired video sampling rate.
response = client.chat.completions.create(
    model="/models/Qwen3-VL-4B-Instruct", 
    messages=messages,
    max_tokens=2048,
    extra_body={
        "mm_processor_kwargs": {
            "fps": 1,                    # 每秒取 1 帧
            "do_sample_frames": True,    # 启用采样
            "max_frame_count": 8         # ⚠️ 强制最多只取 8 帧！
        }
    }
)
print(f"Response costs: {time.time() - start:.2f}s")
print(f"Generated text: {response.choices[0].message.content}")