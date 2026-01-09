import time
from openai import OpenAI
import base64
import os

# 1. 配置客户端
client = OpenAI(
    api_key="EMPTY",
    base_url="http://127.0.0.1:8000/v1",
    timeout=3600
)
#docker run --gpus all --ipc=host -p 8000:8000 --rm --name qwen3vl -v J:/models/LLM/Qwen-VL:/models:ro -it qwenllm/qwenvl:qwen3vl-cu128 bash
#vllm serve /models/Qwen3-VL-8B-Instruct   --dtype half   --gpu-memory-utilization 0.9   --max-model-len 30000   --host 0.0.0.0   --port 8000   --enable-chunked-prefill --media-io-kwargs '{"video": {"num_frames": -1}}'
# # 2. 指定你的本地图片路径
image_path = r"J:\AI-T8-video-onekey-20251005\ComfyUI\output\wan2.2chu_02500.png" # ✅ 修改为你自己的图片路径

# 3. 检查文件是否存在
if not os.path.exists(image_path):
    raise FileNotFoundError(f"图片文件不存在: {image_path}")

# 4. 读取图片并转为 base64
with open(image_path, "rb") as f:
    encoded_image = base64.b64encode(f.read()).decode("utf-8")

# 5. 构造 data URL（关键！）
image_url = f"data:image/jpeg;base64,{encoded_image}"  # 如果是 PNG，改为 image/png

# 6. 构造消息
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url  # ✅ 使用 base64 编码的本地图片
                }
            },
            {
                "type": "text",
                "text": "详细描述图片"
            }
        ]
    }
]

print("正在发送请求...")
start = time.time()

try:
    response = client.chat.completions.create(
        model="/models/Qwen3-VL-8B-Instruct",  # 必须和你加载的模型名一致
        messages=messages,
        max_tokens=1024,
        temperature=0.1
    )
    print(f"✅ 推理完成，耗时: {time.time() - start:.2f}s")
    print(f"🔍 识别结果:\n{response.choices[0].message.content}")
except Exception as e:
    print(f"❌ 请求失败: {e}")