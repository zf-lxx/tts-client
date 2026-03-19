"""
TTS 服务层
"""
import uuid
import os
import json
import time
from typing import List, Optional, Dict
from datetime import datetime

from models.schemas import (
    TTSSpeechRequest,
    TTSPreviewRequest,
    VoiceInfo,
    VoiceListResponse,
    TTSHistoryItem,
    ChannelType
)
from config.settings import settings
from config.logger import logger
from .channel_service import channel_service
from .providers import (
    TTSProvider,
    OpenAIProvider,
    EdgeTTSProvider,
    AzureTTSProvider,
    VolcengineTTSProvider,
    NamiTTSProvider,
)


class TTSChannelManager:
    """TTS 渠道管理器"""

    VOICE_CACHE_TTL = 300  # 音色列表缓存时间（秒）

    def __init__(self):
        self.history: List[TTSHistoryItem] = []
        self.history_file = os.path.join("./data", "history.json")
        self._voice_cache: Dict[str, List[VoiceInfo]] = {}
        self._voice_cache_time: Dict[str, float] = {}
        os.makedirs(settings.AUDIO_OUTPUT_DIR, exist_ok=True)
        self._load_history()

    def _load_history(self):
        """加载历史记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = [TTSHistoryItem(**item) for item in data]
            except Exception as e:
                logger.error(f"加载历史记录失败: {e}")
                self.history = []

    def _save_history(self):
        """保存历史记录"""
        try:
            data = [json.loads(item.model_dump_json()) for item in self.history]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")

    def clear_history(self):
        """清空历史记录"""
        self.history = []
        self._save_history()

    def _get_provider(self, channel_config: dict) -> TTSProvider:
        """根据渠道类型获取提供商实例"""
        channel_type = channel_config.get("type")

        if channel_type == ChannelType.OPENAI:
            return OpenAIProvider(channel_config)
        elif channel_type == ChannelType.AZURE:
            return AzureTTSProvider(channel_config)
        elif channel_type == ChannelType.EDGE:
            return EdgeTTSProvider(channel_config)
        elif channel_type == ChannelType.NAMI:
            return NamiTTSProvider(channel_config)
        elif channel_type == ChannelType.CUSTOM and channel_config.get("config", {}).get("provider") == "volcengine":
            return VolcengineTTSProvider(channel_config)
        else:
            return EdgeTTSProvider(channel_config)

    def _get_default_channel_id(self) -> Optional[str]:
        """获取默认渠道ID（优先级最高的活跃渠道）"""
        active = [c for c in channel_service.channels.values() if c.get("status") == "active"]
        if not active:
            return None
        active.sort(key=lambda x: x.get("priority", 0), reverse=True)
        return active[0].get("id")

    def _get_available_channel(self) -> Optional[dict]:
        """获取任意可用渠道"""
        for channel in channel_service.channels.values():
            if channel.get("status") == "active":
                return channel
        return None

    async def get_channel_id_by_voice(self, voice: str) -> Optional[str]:
        """根据音色名查找所属渠道ID（带缓存）"""
        now = time.time()
        for channel_id, channel_config in channel_service.channels.items():
            if channel_config.get("status") != "active":
                continue
            if (
                channel_id in self._voice_cache
                and now - self._voice_cache_time.get(channel_id, 0) < self.VOICE_CACHE_TTL
            ):
                voices = self._voice_cache[channel_id]
            else:
                provider = self._get_provider(channel_config)
                try:
                    voices = await provider.get_voices()
                    self._voice_cache[channel_id] = voices
                    self._voice_cache_time[channel_id] = now
                except Exception:
                    continue
            for v in voices:
                if v.id == voice:
                    return channel_id
        return None

    async def synthesize(self, request: TTSSpeechRequest) -> tuple[bytes, str]:
        """
        合成语音
        返回: (音频数据, 文件格式)
        """
        logger.info(f"收到合成请求: text={request.input[:20]}..., voice={request.voice}, channel_id={request.channel_id}")

        if request.channel_id:
            channel_id = request.channel_id
        else:
            # 根据音色自动匹配渠道，找不到则降级到默认渠道
            channel_id = await self.get_channel_id_by_voice(request.voice)
            if channel_id:
                logger.info(f"音色 {request.voice} 自动匹配到渠道: {channel_id}")
            else:
                channel_id = self._get_default_channel_id()

        channel_config = channel_service.channels.get(channel_id)

        if not channel_config or channel_config.get("status") != "active":
            logger.warning(f"渠道 {channel_id} 不可用，尝试寻找备用渠道")
            channel_config = self._get_available_channel()
            if not channel_config:
                raise Exception("没有可用的 TTS 渠道")

        logger.info(f"使用渠道: {channel_config['name']} ({channel_config['id']})")

        provider = self._get_provider(channel_config)
        try:
            audio_data = await provider.synthesize(request)
            logger.info(f"语音合成成功，大小: {len(audio_data)} bytes")
        except Exception as e:
            logger.error(f"语音合成失败: {str(e)}", exc_info=True)
            raise

        history_item = TTSHistoryItem(
            id=str(uuid.uuid4()),
            text=request.input[:100] + "..." if len(request.input) > 100 else request.input,
            voice=request.voice,
            channel_id=channel_config["id"],
            format=request.response_format.value,
            speed=request.speed,
            created_at=datetime.now(),
            file_size=len(audio_data)
        )
        self.history.insert(0, history_item)
        if len(self.history) > 7:
            self.history = self.history[:7]
        self._save_history()

        file_path = os.path.join(settings.AUDIO_OUTPUT_DIR, f"{history_item.id}.{request.response_format.value}")
        with open(file_path, "wb") as f:
            f.write(audio_data)

        return audio_data, request.response_format.value

    async def preview(self, request: TTSPreviewRequest) -> bytes:
        """预览语音（不记录历史）"""
        channel_id = request.channel_id or self._get_default_channel_id()
        channel_config = channel_service.channels.get(channel_id)

        if not channel_config or channel_config.get("status") != "active":
            channel_config = self._get_available_channel()
            if not channel_config:
                raise Exception("没有可用的 TTS 渠道")

        # 将 TTSPreviewRequest 转为 TTSSpeechRequest
        speech_request = TTSSpeechRequest(
            input=request.text,
            voice=request.voice,
            speed=request.speed,
            pitch=request.pitch,
            volume=request.volume,
            response_format=request.response_format,
            channel_id=channel_id,
        )

        provider = self._get_provider(channel_config)
        return await provider.synthesize(speech_request)

    async def get_voices(self, channel_id: Optional[str] = None) -> VoiceListResponse:
        """获取指定渠道的语音列表"""
        if channel_id:
            channel_config = channel_service.channels.get(channel_id)
            if not channel_config:
                raise ValueError(f"渠道 {channel_id} 不存在")
        else:
            channel_id = self._get_default_channel_id()
            channel_config = channel_service.channels.get(channel_id) if channel_id else None
            if not channel_config:
                raise ValueError("没有可用的渠道")

        provider = self._get_provider(channel_config)
        voices = await provider.get_voices()
        return VoiceListResponse(
            channel_id=channel_config["id"],
            voices=voices
        )

    def get_history(self, limit: int = 50) -> List[TTSHistoryItem]:
        return self.history[:limit]


tts_manager = TTSChannelManager()
