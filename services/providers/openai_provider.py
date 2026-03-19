import httpx
from typing import List

from models.schemas import TTSSpeechRequest, VoiceInfo
from config.logger import logger
from .base import TTSProvider


class OpenAIProvider(TTSProvider):
    """OpenAI TTS 提供商"""

    async def synthesize(self, request: TTSSpeechRequest) -> bytes:
        """调用 OpenAI API 合成语音"""
        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", "https://api.openai.com/v1")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": request.model,
            "input": request.input,
            "voice": request.voice,
            "response_format": request.response_format.value,
            "speed": request.speed
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/audio/speech",
                headers=headers,
                json=payload,
                timeout=60.0
            )
            response.raise_for_status()
            return response.content

    async def get_voices(self) -> List[VoiceInfo]:
        """OpenAI 支持的语音列表"""
        api_key = self.config.get("api_key", "")
        base_url = self.config.get("base_url", "https://api.openai.com/v1")

        # 如果是官方 API，返回固定列表
        if "api.openai.com" in base_url:
            return [
                VoiceInfo(id="alloy", name="Alloy", gender="neutral", description="通用中性声音"),
                VoiceInfo(id="echo", name="Echo", gender="male", description="男性声音"),
                VoiceInfo(id="fable", name="Fable", gender="male", description="英国男性"),
                VoiceInfo(id="onyx", name="Onyx", gender="male", description="低沉男性"),
                VoiceInfo(id="nova", name="Nova", gender="female", description="女性声音"),
                VoiceInfo(id="shimmer", name="Shimmer", gender="female", description="明亮女性"),
            ]

        # 第三方 API，尝试动态获取
        try:
            logger.info(f"正在从第三方接口获取音色列表: {base_url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    voices = []

                    # 优先检查非标准的 voices 字段 (字典格式: {"id": "name"})
                    # 适配部分第三方 API (如用户提供的 Qwen-TTS 格式)
                    if "voices" in data and isinstance(data["voices"], dict):
                        for voice_id, voice_name in data["voices"].items():
                            voices.append(VoiceInfo(
                                id=voice_id,
                                name=str(voice_name),
                                description="第三方接口音色"
                            ))
                        if voices:
                            logger.info(f"从 voices 字段获取到 {len(voices)} 个音色")
                            return voices

                    # 标准 OpenAI 格式: data 列表
                    models = data.get("data", [])
                    for model in models:
                        model_id = model.get("id") if isinstance(model, dict) else str(model)
                        name = model.get("name", model_id) if isinstance(model, dict) else model_id
                        voices.append(VoiceInfo(
                            id=model_id,
                            name=name,
                            description="第三方接口音色"
                        ))

                    if voices:
                        logger.info(f"获取到 {len(voices)} 个音色")
                        return voices
        except Exception as e:
            logger.warning(f"从第三方接口获取音色失败: {str(e)}，使用默认列表")

        # 获取失败或无数据，返回默认列表作为保底
        return [
            VoiceInfo(id="alloy", name="Alloy", description="默认音色"),
            VoiceInfo(id="echo", name="Echo", description="默认音色"),
            VoiceInfo(id="fable", name="Fable", description="默认音色"),
            VoiceInfo(id="onyx", name="Onyx", description="默认音色"),
            VoiceInfo(id="nova", name="Nova", description="默认音色"),
            VoiceInfo(id="shimmer", name="Shimmer", description="默认音色"),
        ]
