"""
数据模型定义
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class AudioFormat(str, Enum):
    """支持的音频格式"""
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    AAC = "aac"
    PCM = "pcm"


class TTSSpeechRequest(BaseModel):
    """TTS 语音合成请求 - 兼容 OpenAI 格式"""
    model: str = Field(default="tts-1", description="模型标识")
    input: str = Field(..., description="要合成的文本内容", min_length=1, max_length=5000)
    voice: str = Field(default="alloy", description="语音标识")
    response_format: AudioFormat = Field(default=AudioFormat.MP3, description="输出音频格式")
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="语速，范围 0.25-4.0")
    channel_id: Optional[str] = Field(default=None, description="指定使用的渠道ID")
    pitch: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="音调，范围 0.5-2.0")
    volume: Optional[float] = Field(default=1.0, ge=0.0, le=2.0, description="音量，范围 0.0-2.0")


class TTSPreviewRequest(BaseModel):
    """TTS 预览请求"""
    text: str = Field(..., min_length=1, max_length=500, description="预览文本")
    voice: str = Field(default="alloy", description="语音标识")
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    pitch: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    channel_id: Optional[str] = Field(default=None)
    response_format: AudioFormat = Field(default=AudioFormat.MP3)


class ChannelType(str, Enum):
    """渠道类型"""
    OPENAI = "openai"
    AZURE = "azure"
    GOOGLE = "google"
    ELEVENLABS = "elevenlabs"
    EDGE = "edge"
    CUSTOM = "custom"
    LOCAL = "local"
    NAMI = "nami"


class ChannelStatus(str, Enum):
    """渠道状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ChannelCreateRequest(BaseModel):
    """创建渠道请求"""
    name: str = Field(..., min_length=1, max_length=100, description="渠道名称")
    type: ChannelType = Field(..., description="渠道类型")
    base_url: Optional[str] = Field(default=None, description="API 基础地址")
    api_key: Optional[str] = Field(default=None, description="API 密钥")
    config: Dict[str, Any] = Field(default_factory=dict, description="额外配置")
    priority: int = Field(default=0, ge=0, description="优先级，数字越大优先级越高")
    is_default: bool = Field(default=False, description="是否为默认渠道")


class ChannelUpdateRequest(BaseModel):
    """更新渠道请求"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(default=None)
    api_key: Optional[str] = Field(default=None)
    config: Optional[Dict[str, Any]] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=0)
    status: Optional[ChannelStatus] = Field(default=None)
    is_default: Optional[bool] = Field(default=None)


class ChannelResponse(BaseModel):
    """渠道响应"""
    id: str
    name: str
    type: ChannelType
    base_url: Optional[str]
    config: Dict[str, Any]
    priority: int
    status: ChannelStatus
    is_default: bool
    created_at: datetime
    updated_at: datetime


class ChannelListResponse(BaseModel):
    """渠道列表响应"""
    total: int
    items: List[ChannelResponse]


class VoiceInfo(BaseModel):
    """语音信息"""
    id: str
    name: str
    gender: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    preview_url: Optional[str] = None


class VoiceListResponse(BaseModel):
    """语音列表响应"""
    channel_id: str
    voices: List[VoiceInfo]


class TTSHistoryItem(BaseModel):
    """TTS 历史记录"""
    id: str
    text: str
    voice: str
    channel_id: str
    format: str
    speed: float
    created_at: datetime
    file_size: Optional[int] = None
    duration: Optional[float] = None


class APIResponse(BaseModel):
    """通用 API 响应"""
    success: bool
    message: str
    data: Optional[Any] = None
