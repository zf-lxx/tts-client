import asyncio
import io
from typing import List

from models.schemas import TTSSpeechRequest, VoiceInfo
from config.logger import logger
from .base import TTSProvider


class EdgeTTSProvider(TTSProvider):
    """Microsoft Edge TTS 提供商（免费）"""

    async def synthesize(self, request: TTSSpeechRequest) -> bytes:
        """使用 Edge TTS 合成语音"""
        try:
            import edge_tts
        except ImportError:
            raise ImportError("请安装 edge-tts: pip install edge-tts")

        rate_value = int((request.speed - 1) * 100)
        rate_str = f"{rate_value:+d}%"

        volume_value = int((request.volume - 1) * 100)
        volume_str = f"{volume_value:+d}%"

        communicate = edge_tts.Communicate(
            text=request.input,
            voice=request.voice,
            rate=rate_str,
            volume=volume_str
        )

        audio_data = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.write(chunk["data"])

        return audio_data.getvalue()

    async def get_voices(self) -> List[VoiceInfo]:
        """获取 Edge TTS 语音列表"""
        fallback_voices = [
            VoiceInfo(id="zh-CN-XiaoxiaoNeural", name="晓晓 (中文女)", gender="Female", language="zh-CN"),
            VoiceInfo(id="zh-CN-YunxiNeural", name="云希 (中文男)", gender="Male", language="zh-CN"),
            VoiceInfo(id="zh-CN-YunjianNeural", name="云健 (中文男)", gender="Male", language="zh-CN"),
            VoiceInfo(id="zh-CN-XiaoyiNeural", name="晓伊 (中文女)", gender="Female", language="zh-CN"),
            VoiceInfo(id="en-US-GuyNeural", name="Guy (English Male)", gender="Male", language="en-US"),
            VoiceInfo(id="en-US-JennyNeural", name="Jenny (English Female)", gender="Female", language="en-US"),
            VoiceInfo(id="ja-JP-NanamiNeural", name="Nanami (Japanese)", gender="Female", language="ja-JP"),
            VoiceInfo(id="ko-KR-SunHiNeural", name="SunHi (Korean)", gender="Female", language="ko-KR"),
        ]

        try:
            import edge_tts
            logger.info("尝试从 Edge TTS 获取在线语音列表...")

            try:
                voices = await asyncio.wait_for(edge_tts.list_voices(), timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("Edge TTS 获取超时，使用预置列表")
                return fallback_voices
            except Exception as e:
                logger.warning(f"Edge TTS 获取出错: {e}，使用预置列表")
                return fallback_voices

            if not voices:
                logger.warning("Edge TTS 返回空列表，使用预置列表")
                return fallback_voices

            result_voices = [
                VoiceInfo(
                    id=v["ShortName"],
                    name=f"{v['FriendlyName']} ({v.get('Locale', '')})",
                    gender=v.get("Gender", "unknown"),
                    language=v.get("Locale", "")
                )
                for v in voices
            ]
            logger.info(f"成功获取 Edge TTS 语音列表: {len(result_voices)} 个")
            return result_voices

        except ImportError:
            logger.error("未安装 edge-tts 库，使用预置列表")
            return fallback_voices
        except Exception as e:
            logger.error(f"获取 Edge TTS 语音列表失败: {str(e)}，使用预置列表")
            return fallback_voices
