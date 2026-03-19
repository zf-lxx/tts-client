from typing import List
from models.schemas import TTSSpeechRequest, VoiceInfo


class TTSProvider:
    """TTS 提供商基类"""

    def __init__(self, channel_config: dict):
        self.config = channel_config
        self.channel_id = channel_config.get("id")
        self.channel_type = channel_config.get("type")

    async def synthesize(self, request: TTSSpeechRequest) -> bytes:
        """合成语音"""
        raise NotImplementedError

    async def get_voices(self) -> List[VoiceInfo]:
        """获取可用语音列表"""
        raise NotImplementedError

    async def health_check(self) -> bool:
        """健康检查"""
        return True
