"""
OpenAI API 兼容的 TTS 服务端点
提供 /v1/audio/speech 接口，兼容 openai-python SDK
"""
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn
from tts_adapter import TTSAAdapter

app = FastAPI(title="TTS OpenAI Compatible Server")
tts_adapter = TTSAAdapter()


class CreateSpeechRequest(BaseModel):
    model: str
    input: str
    voice: str = "alloy"  # alloy, echo, fable, onyx, nova, shimmer
    response_format: str = "mp3"  # mp3, wav, flac, opus


@app.get("/v1/models")
async def list_models():
    """列出可用的 TTS 模型"""
    return {
        "object": "list",
        "data": [
            {
                "id": "tts-0.6B",
                "object": "model",
                "created": 1712345678,
                "owned_by": "local"
            }
        ]
    }


@app.post("/v1/audio/speech")
async def create_speech(request: CreateSpeechRequest):
    """生成语音 - OpenAI API 兼容端点"""
    try:
        # 映射 voice
        voice_map = {
            "alloy": "少女音1",
            "echo": "御姐",
            "fable": "萝莉1",
            "onyx": "老男人",
            "nova": "少女音2",
            "shimmer": "少女音3"
        }
        
        selected_voice = voice_map.get(request.voice, "少女音1")
        
        # 调用本地 TTS 服务
        result = tts_adapter.generate_tts(
            text=request.input,
            voice=selected_voice,
            speed=1.0,
            response_format=request.response_format
        )
        
        return response_from_result(result, request.response_format)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def response_from_result(result, format_type):
    """根据结果创建响应"""
    if isinstance(result, tuple) and len(result) > 1:
        audio_path = result[0]
    else:
        audio_path = result
    
    import os
    from fastapi.responses import StreamingResponse
    
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not generated")
    
    # 根据格式设置 Content-Type
    mime_types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "flac": "audio/flac",
        "opus": "audio/opus"
    }
    
    content_type = mime_types.get(format_type, "audio/wav")
    
    def iterfile():
        with open(audio_path, "rb") as f:
            yield from f
    
    return StreamingResponse(iterfile(), media_type=content_type)


@app.post("/v1/audio/speech/advanced")
async def create_speech_advanced(
    text: str = Query(..., description="要转换的文本"),
    voice: str = Query("少女音1", description="音色选择"),
    speed: float = Query(1.0, ge=0.5, le=2.0, description="语速 (0.5-2.0)"),
    temperature: float = Query(0.6, ge=0.0, le=1.0, description="温度参数"),
    response_format: str = Query("wav", description="输出格式")
):
    """高级 TTS 端点，支持更多参数"""
    try:
        result = tts_adapter.generate_tts(
            text=text,
            voice=voice,
            speed=speed,
            temperature=temperature,
            response_format=response_format
        )
        
        return response_from_result(result, response_format)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
