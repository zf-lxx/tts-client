import uuid
import base64
import hashlib
import hmac
import html
import json
import os
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from urllib.parse import quote

import httpx

from models.schemas import TTSSpeechRequest, VoiceInfo, AudioFormat
from config.logger import logger
from .base import TTSProvider


AZURE_ENDPOINT_URL = "https://dev.microsofttranslator.com/apps/endpoint?api-version=1.0"
AZURE_VOICES_LIST_URL = "https://eastus.api.speech.microsoft.com/cognitiveservices/voices/list"
AZURE_USER_AGENT = "okhttp/4.5.0"
AZURE_CLIENT_VERSION = "4.0.530a 5fe1dc6c"
AZURE_USER_ID = "0f04d16a175c411e"
AZURE_HOME_GEOGRAPHIC_REGION = "zh-Hans-CN"
AZURE_CLIENT_TRACE_ID = "aab069b9-70a7-4844-a734-96cd78d94be9"
AZURE_VOICE_DECODE_KEY = "oik6PdDdMnOXemTbwvMn9de/h9lFnfBaCWbGMMZqqoSaQaqUOqjVGm5NqsmjcBI1x+sS9ugjB55HEJWRiFXYFw=="
AZURE_DEFAULT_VOICE_NAME = "zh-CN-XiaoxiaoMultilingualNeural"
AZURE_DEFAULT_OUTPUT_FORMAT = "audio-24khz-48kbitrate-mono-mp3"
AZURE_DEFAULT_STYLE = "general"

_azure_endpoint: Optional[Dict[str, Any]] = None
_azure_expired_at: Optional[int] = None
_azure_voice_list_cache: Optional[List[Dict[str, Any]]] = None


def _load_azure_voice_catalog() -> List[Dict[str, Any]]:
    """加载 Azure 语音与情感映射表"""
    from config.settings import settings
    file_path = os.path.join(settings.DATA_DIR, "azure_voices.json")
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"读取 Azure 语音配置失败: {e}")
        return []


AZURE_VOICE_CATALOG = _load_azure_voice_catalog()


def _azure_sign(url_str: str) -> str:
    url_without_scheme = url_str.split("://")[1]
    encoded_url = quote(url_without_scheme, safe="")
    uuid_str = str(uuid.uuid4()).replace("-", "")
    formatted_date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S").lower() + "gmt"
    bytes_to_sign = f"MSTranslatorAndroidApp{encoded_url}{formatted_date}{uuid_str}".lower().encode("utf-8")
    decode = base64.b64decode(AZURE_VOICE_DECODE_KEY)
    hmac_sha256 = hmac.new(decode, bytes_to_sign, hashlib.sha256)
    secret_key = hmac_sha256.digest()
    sign_base64 = base64.b64encode(secret_key).decode()
    return f"MSTranslatorAndroidApp::{sign_base64}::{formatted_date}::{uuid_str}"


def _azure_get_endpoint() -> Dict[str, Any]:
    signature = _azure_sign(AZURE_ENDPOINT_URL)
    headers = {
        "Accept-Language": "zh-Hans",
        "X-ClientVersion": AZURE_CLIENT_VERSION,
        "X-UserId": AZURE_USER_ID,
        "X-HomeGeographicRegion": AZURE_HOME_GEOGRAPHIC_REGION,
        "X-ClientTraceId": AZURE_CLIENT_TRACE_ID,
        "X-MT-Signature": signature,
        "User-Agent": AZURE_USER_AGENT,
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": "0",
        "Accept-Encoding": "gzip",
    }
    response = httpx.post(AZURE_ENDPOINT_URL, headers=headers, timeout=10.0)
    response.raise_for_status()
    return response.json()


def _azure_get_ssml(text: str, voice_name: str, rate: str, pitch: str, style: str) -> str:
    escaped_text = html.escape(text)
    return f"""
<speak xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" version="1.0" xml:lang="zh-CN">
<voice name="{voice_name}">
    <mstts:express-as style="{style}" styledegree="1.0" role="default">
        <prosody rate="{rate}%" pitch="{pitch}%">
            {escaped_text}
        </prosody>
    </mstts:express-as>
</voice>
</speak>
    """


def _build_voice_options(raw_list: List[Dict[str, Any]]) -> List[VoiceInfo]:
    """将原始语音列表转换为 VoiceInfo，并追加情感风格变体"""
    voice_options: List[VoiceInfo] = []
    for v in raw_list:
        voice_id = v.get("ShortName", v.get("Name", ""))
        voice_name = v.get("FriendlyName", v.get("Name", ""))
        voice_options.append(VoiceInfo(
            id=voice_id,
            name=voice_name,
            gender=v.get("Gender"),
            language=v.get("Locale"),
            description=v.get("Status")
        ))
        if AZURE_VOICE_CATALOG:
            catalog_item = next(
                (item for item in AZURE_VOICE_CATALOG if item.get("name") == voice_id), None
            )
            if catalog_item:
                for emotion in catalog_item.get("emotions", []):
                    emotion_name = emotion.get("name")
                    emotion_label = emotion.get("label")
                    if emotion_name:
                        voice_options.append(VoiceInfo(
                            id=f"{voice_id}|{emotion_name}",
                            name=f"{voice_name} - {emotion_label or emotion_name}",
                            gender=v.get("Gender"),
                            language=v.get("Locale"),
                            description="风格"
                        ))
    return voice_options


class AzureTTSProvider(TTSProvider):
    """Azure 内置 TTS 提供商"""

    async def synthesize(self, request: TTSSpeechRequest) -> bytes:
        """使用 Azure 内置渠道合成语音"""
        global _azure_endpoint, _azure_expired_at

        current_time = int(time.time())
        if not _azure_expired_at or current_time > _azure_expired_at - 60:
            _azure_endpoint = _azure_get_endpoint()
            jwt = _azure_endpoint["t"].split(".")[1]
            decoded_jwt = json.loads(base64.b64decode(jwt + "==").decode("utf-8"))
            _azure_expired_at = decoded_jwt["exp"]
        if not _azure_endpoint:
            raise RuntimeError("Azure endpoint 获取失败")

        if request.voice and request.voice != "alloy":
            voice_name = request.voice
        else:
            voice_name = self.config.get("voice", AZURE_DEFAULT_VOICE_NAME)

        if "|" in voice_name:
            voice_name, style_override = voice_name.split("|", 1)
        else:
            style_override = None

        rate_value = int((request.speed - 1) * 100)
        pitch_value = int((request.pitch - 1) * 100) if request.pitch is not None else 0
        rate = self.config.get("rate", f"{rate_value}")
        pitch = self.config.get("pitch", f"{pitch_value}")
        style = style_override or self.config.get("style", AZURE_DEFAULT_STYLE)

        output_format = self.config.get("output_format")
        if not output_format:
            format_map = {
                AudioFormat.MP3: AZURE_DEFAULT_OUTPUT_FORMAT,
                AudioFormat.WAV: "riff-24khz-16bit-mono-pcm",
                AudioFormat.PCM: "raw-24khz-16bit-mono-pcm",
                AudioFormat.OGG: "ogg-24khz-16bit-mono-opus",
                AudioFormat.AAC: "audio-24khz-48kbitrate-mono-aac",
            }
            output_format = format_map.get(request.response_format, AZURE_DEFAULT_OUTPUT_FORMAT)

        url = f"https://{_azure_endpoint['r']}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Authorization": _azure_endpoint["t"],
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": output_format,
        }

        ssml = _azure_get_ssml(request.input, voice_name, rate, pitch, style)

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, content=ssml.encode("utf-8"), timeout=30.0)
            response.raise_for_status()
            return response.content

    async def get_voices(self) -> List[VoiceInfo]:
        """获取 Azure 语音列表"""
        global _azure_voice_list_cache

        if _azure_voice_list_cache is not None:
            return _build_voice_options(_azure_voice_list_cache)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.26",
            "X-Ms-Useragent": "SpeechStudio/2021.05.001",
            "Content-Type": "application/json",
            "Origin": "https://azure.microsoft.com",
            "Referer": "https://azure.microsoft.com",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(AZURE_VOICES_LIST_URL, headers=headers, timeout=10.0)
            response.raise_for_status()
            result = response.json()

        if isinstance(result, list):
            _azure_voice_list_cache = result

        return _build_voice_options(result or [])
