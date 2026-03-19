"""
渠道管理路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from models.schemas import (
    ChannelCreateRequest,
    ChannelUpdateRequest,
    ChannelResponse,
    ChannelListResponse,
    ChannelType,
    ChannelStatus,
    APIResponse
)
from services import channel_service

router = APIRouter()


@router.post("/channels", response_model=APIResponse)
async def create_channel(request: ChannelCreateRequest):
    """
    创建 TTS 渠道
    
    支持多种渠道类型：OpenAI、Azure、Google、ElevenLabs、Edge、Custom
    """
    try:
        channel = channel_service.create_channel(request)
        return APIResponse(
            success=True,
            message="渠道创建成功",
            data=channel.model_dump()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/channels", response_model=APIResponse)
async def list_channels(
    status: Optional[ChannelStatus] = Query(None, description="按状态筛选"),
    channel_type: Optional[ChannelType] = Query(None, description="按类型筛选")
):
    """
    获取渠道列表
    
    支持按状态和类型筛选
    """
    try:
        result = channel_service.list_channels(status, channel_type)
        return APIResponse(
            success=True,
            message="获取成功",
            data={
                "total": result.total,
                "items": [item.model_dump() for item in result.items]
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取渠道列表失败: {str(e)}")


@router.get("/channels/{channel_id}", response_model=APIResponse)
async def get_channel(channel_id: str):
    """
    获取单个渠道详情
    """
    channel = channel_service.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="渠道不存在")
    
    return APIResponse(
        success=True,
        message="获取成功",
        data=channel.model_dump()
    )


@router.put("/channels/{channel_id}", response_model=APIResponse)
async def update_channel(channel_id: str, request: ChannelUpdateRequest):
    """
    更新渠道信息
    """
    try:
        channel = channel_service.update_channel(channel_id, request)
        return APIResponse(
            success=True,
            message="渠道更新成功",
            data=channel.model_dump()
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/channels/{channel_id}", response_model=APIResponse)
async def delete_channel(channel_id: str):
    """
    删除渠道
    
    注意：不能删除默认渠道
    """
    try:
        success = channel_service.delete_channel(channel_id)
        if success:
            return APIResponse(success=True, message="渠道删除成功")
        else:
            raise HTTPException(status_code=404, detail="渠道不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/channels/{channel_id}/test", response_model=APIResponse)
async def test_channel(channel_id: str):
    """
    测试渠道连接
    
    验证渠道配置是否正确
    """
    result = await channel_service.test_channel(channel_id)
    return APIResponse(
        success=result["success"],
        message=result["message"]
    )


@router.get("/channel-types", response_model=APIResponse)
async def get_channel_types():
    """
    获取支持的渠道类型列表
    """
    types = [
        {"value": ChannelType.OPENAI, "label": "OpenAI", "description": "OpenAI TTS API"},
        {"value": ChannelType.AZURE, "label": "Azure", "description": "Azure Speech Services"},
        {"value": ChannelType.GOOGLE, "label": "Google", "description": "Google Cloud Text-to-Speech"},
        {"value": ChannelType.ELEVENLABS, "label": "ElevenLabs", "description": "ElevenLabs API"},
        {"value": ChannelType.EDGE, "label": "Edge TTS", "description": "Microsoft Edge TTS (免费)"},
        {"value": ChannelType.CUSTOM, "label": "Custom", "description": "自定义 API"},
        {"value": ChannelType.LOCAL, "label": "Local", "description": "本地 TTS 引擎"},
    ]
    
    return APIResponse(
        success=True,
        message="获取成功",
        data=types
    )
