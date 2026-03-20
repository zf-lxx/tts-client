import hashlib
import json
import os
import random
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import List

import httpx

from models.schemas import TTSSpeechRequest, VoiceInfo
from config.logger import logger
from .base import TTSProvider


NAMI_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
from config.settings import settings
NAMI_VOICES_FILE = os.path.join(settings.DATA_DIR, "nami_voices.json")
NAMI_ROBOTS_URL = "https://bot.n.cn/api/robot/platform"
NAMI_TTS_URL = "https://bot.n.cn/api/tts/v1"


def _md5(msg: str) -> str:
    return hashlib.md5(msg.encode("utf-8")).hexdigest()


def _e(nt: str) -> int:
    HASH_MASK_1 = 268435455
    HASH_MASK_2 = 266338304
    at = 0
    for i in range(len(nt) - 1, -1, -1):
        st = ord(nt[i])
        at = ((at << 6) & HASH_MASK_1) + st + (st << 14)
        it = at & HASH_MASK_2
        if it != 0:
            at = at ^ (it >> 21)
    return at


def _generate_unique_hash() -> int:
    lang = "zh-CN"
    app_name = "chrome"
    ver = 1.0
    platform = "Win32"
    width = 1920
    height = 1080
    color_depth = 24
    referrer = "https://bot.n.cn/chat"
    nt = f"{app_name}{ver}{lang}{platform}{NAMI_UA}{width}x{height}{color_depth}{referrer}"
    at = len(nt)
    it = 1
    while it:
        nt += str(it ^ at)
        it -= 1
        at += 1
    return (round(random.random() * 2147483647) ^ _e(nt)) * 2147483647


def _generate_mid() -> str:
    domain = "https://bot.n.cn"
    rt = str(_e(domain)) + str(_generate_unique_hash()) + str(int(time.time() * 1000) + random.random() + random.random())
    return rt.replace(".", "e")[:32]


def _get_headers() -> dict:
    device = "Web"
    ver = "1.2"
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")
    access_token = _generate_mid()
    zm_ua = _md5(NAMI_UA)
    zm_token = _md5(f"{device}{timestamp}{ver}{access_token}{zm_ua}")
    return {
        "device-platform": device,
        "timestamp": timestamp,
        "access-token": access_token,
        "zm-token": zm_token,
        "zm-ver": ver,
        "zm-ua": zm_ua,
        "User-Agent": NAMI_UA,
    }


def _load_nami_voices(force_refresh: bool = False) -> dict:
    """加载纳米音色列表，优先从本地缓存读取"""
    os.makedirs(os.path.dirname(NAMI_VOICES_FILE), exist_ok=True)
    try:
        if force_refresh or not os.path.exists(NAMI_VOICES_FILE):
            req = urllib.request.Request(NAMI_ROBOTS_URL, headers=_get_headers())
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            with open(NAMI_VOICES_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            with open(NAMI_VOICES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

        voices = {}
        for item in data["data"]["list"]:
            voices[item["tag"]] = {"name": item["title"], "iconUrl": item["icon"]}
        return voices
    except Exception as e:
        logger.warning(f"加载纳米音色列表失败: {e}，使用默认音色")
        return {"DeepSeek": {"name": "DeepSeek (默认)", "iconUrl": ""}}


class NamiTTSProvider(TTSProvider):
    """纳米 AI TTS 提供商（https://bot.n.cn）"""

    async def synthesize(self, request: TTSSpeechRequest) -> bytes:
        """调用纳米 TTS API 合成语音"""
        voice = request.voice
        # 若音色是 OpenAI 占位符，使用渠道配置的默认音色
        if not voice or voice == "alloy":
            voice = self.config.get("config", {}).get("default_voice", "DeepSeek")

        headers = _get_headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        form_data = f"text={urllib.parse.quote(request.input)}&audio_type=mp3&format=stream"
        url = f"{NAMI_TTS_URL}?roleid={voice}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=form_data.encode(),
                headers=headers,
                timeout=30.0,
            )
            if not response.is_success:
                logger.error(f"纳米TTS 请求失败: {response.status_code}, body={response.text[:200]}")
                raise Exception(f"纳米TTS 上游错误 {response.status_code}: {response.text[:200]}")
            return response.content

    async def get_voices(self) -> List[VoiceInfo]:
        """获取纳米音色列表"""
        force_refresh = self.config.get("config", {}).get("force_refresh", False)
        voices_dict = _load_nami_voices(force_refresh=force_refresh)
        return [
            VoiceInfo(id=tag, name=info["name"], description="纳米AI")
            for tag, info in voices_dict.items()
        ]
