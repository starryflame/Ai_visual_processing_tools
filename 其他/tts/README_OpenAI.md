# OpenAI API 兼容 TTS 服务

将本地 Gradio TTS 服务封装成 OpenAI API 兼容格式。

## 架构说明

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│ OpenAI SDK  │────▶│ tts_server.py    │────▶│ tts_adapter  │
│ (客户端)    │     │ (FastAPI 服务器)  │     │ (适配器层)   │
└─────────────┘     └──────────────────┘     └──────────────┘
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │ Gradio TTS   │
                                      │ 服务 (:7862) │
                                      └──────────────┘
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `tts_server.py` | FastAPI 服务器，提供 OpenAI 兼容端点 |
| `tts_adapter.py` | 适配器层，将请求转发到 Gradio TTS |
| `test_openai_client.py` | 使用 openai-python SDK 的示例客户端 |
| `test.py` | 原始 Gradio Client 调用方式（保留） |

## 安装依赖

```bash
pip install fastapi uvicorn openai gradio-client
```

## 使用方法

### 1. 启动本地 TTS 服务（Gradio）

确保你的 Gradio TTS 服务正在运行在 `http://localhost:7862/`

### 2. 启动 OpenAI 兼容服务器

```bash
cd 其他/tts
python tts_server.py
```

服务将在 `http://localhost:8000` 启动。

### 3. 使用 OpenAI SDK 调用

#### Python (openai-python)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"
)

response = client.audio.speech.create(
    model="tts-0.6B",
    input="你好世界",
    voice="alloy"  # alloy, echo, fable, onyx, nova, shimmer
)

response.stream_to_file("output.mp3")
```

#### cURL

```bash
curl -X POST "http://localhost:8000/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer not-needed" \
  -d '{
    "model": "tts-0.6B",
    "input": "你好世界",
    "voice": "alloy",
    "response_format": "mp3"
  }' \
  --output output.mp3
```

### 4. 运行示例客户端

```bash
python test_openai_client.py
```

## API 端点

| 端点 | 说明 |
|------|------|
| `GET /v1/models` | 列出可用的 TTS 模型 |
| `POST /v1/audio/speech` | 生成语音（标准 OpenAI 格式） |
| `POST /v1/audio/speech/advanced` | 高级端点，支持更多参数 |

## Voice 映射表

| OpenAI Voice | Gradio TTS Voice |
|--------------|------------------|
| alloy | 少女音 1 |
| echo | 御姐 |
| fable | 萝莉 1 |
| onyx | 老男人 |
| nova | 少女音 2 |
| shimmer | 少女音 3 |

## OpenAI API 格式参数

```json
{
    "model": "tts-0.6B",      // 模型 ID
    "input": "要转换的文本",   // 必需
    "voice": "alloy",         // 音色 (可选，默认 alloy)
    "response_format": "mp3"  // mp3, wav, flac, opus (可选，默认 mp3)
}
```

## 高级 API 参数

`POST /v1/audio/speech/advanced`

| 参数 | 类型 | 说明 |
|------|------|------|
| text | string | 要转换的文本（必需） |
| voice | string | 音色名称（可选，默认"少女音 1"） |
| speed | float | 语速 (0.5-2.0，可选，默认 1.0) |
| temperature | float | 温度参数 (0.0-1.0，可选，默认 0.6) |
| response_format | string | 输出格式（可选，默认 wav） |

示例：
```bash
curl -X POST "http://localhost:8000/v1/audio/speech/advanced?text=你好&voice=御姐&speed=1.2" \
  --output output.wav
```

## 注意事项

1. Gradio TTS 服务必须正在运行在 `http://localhost:7862/`
2. 生成的音频文件保存在临时目录，请及时处理或删除
3. OpenAI SDK 的 voice 参数是固定的 6 种，如需更多音色请使用高级端点
