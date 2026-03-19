import base64
import json
import os
from typing import List, Optional, Dict, Any

import httpx

from models.schemas import TTSSpeechRequest, VoiceInfo
from config.logger import logger
from .base import TTSProvider


def _load_volc_voice_catalog() -> List[Dict[str, Any]]:
    """加载火山语音列表"""
    file_path = os.path.join("./data", "volc_voices.json")
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"读取火山语音配置失败: {e}")
        return []


VOLC_VOICE_CATALOG = _load_volc_voice_catalog()

_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,zh-TW;q=0.6",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Origin": "chrome-extension://klgfhbiooeogdfodpopgppeadghjjemk",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "none",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "accept": "application/json, text/plain, */*",
    "content-type": "application/json",
}


class VolcengineTTSProvider(TTSProvider):
    """火山引擎内置 TTS 提供商（复用 custom 渠道类型）"""

    async def synthesize(self, request: TTSSpeechRequest) -> bytes:
        """使用火山引擎内置渠道合成语音"""
        language: Optional[str] = None
        try:
            async with httpx.AsyncClient() as client:
                detect_resp = await client.post(
                    "https://translate.volcengine.com/web/langdetect/v1/",
                    headers=_HEADERS,
                    json={"text": request.input},
                    timeout=10.0
                )
                if detect_resp.status_code == 200:
                    language = detect_resp.json().get("language", None)
        except Exception:
            language = None

        speaker = request.voice or self.config.get("voice", "volcengine_default")
        if speaker == "alloy":
            speaker = "volcengine_default"

        allowed_voices = {item.get("name") for item in VOLC_VOICE_CATALOG if item.get("name")}
        if allowed_voices and speaker not in allowed_voices:
            speaker = self.config.get("voice", "volcengine_default")

        payload: Dict[str, Any] = {
            "text": request.input,
            "speaker": speaker,
        }
        if language is not None:
            payload["language"] = language

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://translate.volcengine.com/crx/tts/v1/",
                headers=_HEADERS,
                json=payload,
                timeout=20.0
            )
            response.raise_for_status()

        resp = response.json()
        audio = resp.get("audio")
        if audio is None:
            logger.error(resp)
            raise Exception(f"火山语音服务 {speaker} 生成失败，请切换音色后再试一次。")
        audio_data = audio.get("data", None)
        if audio_data is None:
            logger.error(resp)
            raise Exception(f"火山语音服务 {speaker} 数据生成失败。")

        if isinstance(audio_data, str):
            try:
                return base64.b64decode(audio_data)
            except Exception:
                return audio_data.encode("utf-8")

        return audio_data

    async def get_voices(self) -> List[VoiceInfo]:
        """火山引擎语音列表"""
        if VOLC_VOICE_CATALOG:
            return [
                VoiceInfo(
                    id=item.get("name"),
                    name=item.get("label", item.get("name", "")),
                    description="火山内置"
                )
                for item in VOLC_VOICE_CATALOG
                if item.get("name")
            ]

        fallback_voices = self.config.get("voices")
        if isinstance(fallback_voices, list) and fallback_voices:
            return [
                VoiceInfo(id=v.get("id"), name=v.get("name", v.get("id", "")), description=v.get("description"))
                for v in fallback_voices
                if isinstance(v, dict) and v.get("id")
            ]

        return [
            VoiceInfo(id="volcengine_default", name="火山默认", description="占位音色"),
            VoiceInfo(id="volcengine_female", name="火山女声", description="占位音色"),
            VoiceInfo(id="volcengine_male", name="火山男声", description="占位音色"),
        ]
