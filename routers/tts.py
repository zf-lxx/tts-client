"""
TTS 路由 - 兼容 OpenAI 格式 /v1/audio/speech
"""
from fastapi import APIRouter, HTTPException, Response, Query, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import io

from models.schemas import (
    TTSSpeechRequest, 
    TTSPreviewRequest,
    VoiceListResponse,
    TTSHistoryItem,
    APIResponse,
    AudioFormat
)
from services import tts_manager

router = APIRouter()


@router.post("/audio/speech")
async def create_speech(request: TTSSpeechRequest):
    """
    创建语音 - 兼容 OpenAI TTS API 格式
    
    - **model**: 模型标识 (默认: tts-1)
    - **input**: 要合成的文本
    - **voice**: 语音标识 (默认: alloy)
    - **response_format**: 输出格式 (mp3, wav, ogg, aac, pcm)
    - **speed**: 语速 (0.25-4.0)
    - **channel_id**: 指定渠道ID (可选)
    """
    try:
        audio_data, format_type = await tts_manager.synthesize(request)
        
        # 设置 Content-Type
        content_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "aac": "audio/aac",
            "pcm": "audio/pcm"
        }
        
        return Response(
            content=audio_data,
            media_type=content_type_map.get(format_type, "audio/mpeg"),
            headers={
                "Content-Disposition": f"attachment; filename=speech.{format_type}"
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


@router.post("/audio/preview")
async def preview_speech(request: TTSPreviewRequest):
    """
    预览语音 - 用于前端试听
    
    返回音频数据，可直接播放
    """
    try:
        audio_data = await tts_manager.preview(request)
        
        content_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "aac": "audio/aac",
            "pcm": "audio/pcm"
        }
        
        return Response(
            content=audio_data,
            media_type=content_type_map.get(request.response_format.value, "audio/mpeg")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"预览失败: {str(e)}")


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices(channel_id: Optional[str] = Query(None, description="指定渠道ID")):
    """
    获取可用语音列表
    
    返回指定渠道的可用语音列表
    """
    try:
        return await tts_manager.get_voices(channel_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取语音列表失败: {str(e)}")


@router.get("/history")
async def get_history(limit: int = Query(50, ge=1, le=100)):
    """
    获取 TTS 生成历史记录
    
    - **limit**: 返回记录数量 (1-100)
    """
    try:
        history = tts_manager.get_history(limit)
        return APIResponse(
            success=True,
            message="获取成功",
            data=[item.model_dump() for item in history]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@router.delete("/history", response_model=APIResponse)
async def clear_history():
    """
    清空历史记录
    """
    try:
        tts_manager.clear_history()
        return APIResponse(
            success=True,
            message="历史记录已清空"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空历史记录失败: {str(e)}")


@router.get("/audio/stream/{audio_id}")
async def stream_audio(audio_id: str):
    """
    流式播放音频文件
    
    用于历史记录中的音频回放
    """
    import os
    from config.settings import settings
    
    # 查找音频文件
    for fmt in settings.SUPPORTED_FORMATS:
        file_path = os.path.join(settings.AUDIO_OUTPUT_DIR, f"{audio_id}.{fmt}")
        if os.path.exists(file_path):
            content_type_map = {
                "mp3": "audio/mpeg",
                "wav": "audio/wav",
                "ogg": "audio/ogg",
                "aac": "audio/aac",
                "pcm": "audio/pcm"
            }
            
            def iterfile():
                with open(file_path, "rb") as f:
                    yield from f
            
            return StreamingResponse(
                iterfile(),
                media_type=content_type_map.get(fmt, "audio/mpeg")
            )
    
    raise HTTPException(status_code=404, detail="音频文件不存在")


@router.post("/tts/reading")
async def tts_for_reading_app(
    speakText: str = Form(...),
    speakSpeed: int = Form(25),
    voice: Optional[str] = Form(None)
):
    """
    专门为"阅读"APP提供的TTS接口。
    接收 speakText, speakSpeed, 和可选的 voice 参数。
    """
    # 获取默认渠道或根据 voice 定位渠道
    if voice:
        channel_id = await tts_manager.get_channel_id_by_voice(voice)
        if not channel_id:
            raise HTTPException(status_code=404, detail=f"音色 '{voice}' 未找到或未配置")
        selected_voice = voice
    else:
        channel_id = tts_manager._get_default_channel_id()
        if not channel_id:
            raise HTTPException(status_code=500, detail="没有可用的 TTS 渠道")
        voices = await tts_manager.get_voices(channel_id)
        selected_voice = voices.voices[0].id if voices.voices else "alloy"

    # 速度映射：将 5-50 的范围映射到 0.25-4.0
    safe_speak_speed = max(5, min(50, speakSpeed))
    mapped_speed = 0.25 + (safe_speak_speed - 5) / 45.0 * 3.75

    request = TTSSpeechRequest(
        input=speakText,
        voice=selected_voice,
        speed=round(mapped_speed, 2),
        response_format=AudioFormat.MP3,
        channel_id=channel_id
    )

    try:
        audio_data, format_type = await tts_manager.synthesize(request)
        content_type_map = {
            "mp3": "audio/mpeg",
            "wav": "audio/wav",
            "ogg": "audio/ogg",
            "aac": "audio/aac",
            "pcm": "audio/pcm"
        }
        return Response(
            content=audio_data,
            media_type=content_type_map.get(format_type, "audio/mpeg")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")
