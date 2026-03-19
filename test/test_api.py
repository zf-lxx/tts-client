"""
测试标准 OpenAI audio 接口与阅读 App 接口。

用法：
python test/test_api.py --base-url http://127.0.0.1:8000
"""
import argparse
import os
import sys
import time
import uuid

import httpx

AUTH_HEADERS: dict = {}


def parse_args():
    parser = argparse.ArgumentParser(description="TTS API 测试脚本")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="服务地址，默认 http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--api-key",
        default="admin",
        help="API Key，默认 admin",
    )
    parser.add_argument(
        "--out-dir",
        default="./output/audio",
        help="输出目录，默认 ./output/audio",
    )
    parser.add_argument(
        "--text",
        default="今天天气真好，适合出去散步。",
        help="测试文本",
    )
    parser.add_argument(
        "--voice",
        default="alloy",
        help="语音（OpenAI 接口）",
    )
    parser.add_argument(
        "--reading-voice",
        default="",
        help="阅读接口 voice（可选）",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="OpenAI 接口 speed",
    )
    parser.add_argument(
        "--reading-speed",
        type=int,
        default=25,
        help="阅读接口 speakSpeed (5-50)",
    )
    return parser.parse_args()


def save_audio(data: bytes, out_dir: str, prefix: str, ext: str = "mp3") -> str:
    os.makedirs(out_dir, exist_ok=True)
    file_name = f"{prefix}_{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(out_dir, file_name)
    with open(file_path, "wb") as f:
        f.write(data)
    return file_path


def test_health(base_url: str):
    url = f"{base_url.rstrip('/')}/api/health"
    with httpx.Client(timeout=10.0, headers=AUTH_HEADERS) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("status") == "healthy", f"health 响应异常: {data}"
        print(f"[health] ok -> {data}")


def test_openai_audio(base_url: str, text: str, voice: str, speed: float, out_dir: str):
    url = f"{base_url.rstrip('/')}/api/v1/audio/speech"
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": voice,
        "response_format": "mp3",
        "speed": speed,
    }

    with httpx.Client(timeout=60.0, headers=AUTH_HEADERS) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        assert len(resp.content) > 0, "返回音频数据为空"
        assert resp.headers.get("content-type", "").startswith("audio/"), f"content-type 异常: {resp.headers.get('content-type')}"
        audio_path = save_audio(resp.content, out_dir, "openai")
        print(f"[openai] ok -> {audio_path}")


def test_openai_audio_invalid_params(base_url: str):
    """参数校验：文本为空、speed 超范围"""
    url = f"{base_url.rstrip('/')}/api/v1/audio/speech"
    with httpx.Client(timeout=10.0, headers=AUTH_HEADERS) as client:
        # 文本为空
        resp = client.post(url, json={"model": "tts-1", "input": "", "voice": "alloy"})
        assert resp.status_code == 422, f"空文本应返回 422，实际: {resp.status_code}"
        print(f"[openai-invalid] 空文本校验 ok (422)")

        # speed 超范围
        resp = client.post(url, json={"model": "tts-1", "input": "test", "voice": "alloy", "speed": 99.0})
        assert resp.status_code == 422, f"speed 超范围应返回 422，实际: {resp.status_code}"
        print(f"[openai-invalid] speed 超范围校验 ok (422)")


def test_preview(base_url: str, text: str, out_dir: str, channel_id: str):
    url = f"{base_url.rstrip('/')}/api/v1/audio/preview"
    payload = {
        "text": text,
        "voice": "zh-CN-XiaoxiaoNeural",
        "channel_id": channel_id,
        "speed": 1.0,
        "response_format": "mp3",
    }
    with httpx.Client(timeout=60.0, headers=AUTH_HEADERS) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        assert len(resp.content) > 0, "预览音频数据为空"
        audio_path = save_audio(resp.content, out_dir, "preview")
        print(f"[preview] ok -> {audio_path}")


def test_voices(base_url: str) -> tuple[str, str]:
    """获取渠道列表和音色列表，返回 (channel_id, voice_id)"""
    # 先获取渠道列表
    channels_url = f"{base_url.rstrip('/')}/api/v1/channels"
    with httpx.Client(timeout=10.0, headers=AUTH_HEADERS) as client:
        resp = client.get(channels_url)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data", {}).get("items", [])
        assert len(items) > 0, "没有可用渠道"
        channel_id = items[0]["id"]
        print(f"[channels] ok -> {len(items)} 个渠道，使用: {items[0]['name']} ({channel_id})")

    # 获取该渠道音色列表
    voices_url = f"{base_url.rstrip('/')}/api/v1/voices"
    with httpx.Client(timeout=15.0, headers=AUTH_HEADERS) as client:
        resp = client.get(voices_url, params={"channel_id": channel_id})
        resp.raise_for_status()
        data = resp.json()
        voices = data.get("voices", [])
        assert len(voices) > 0, f"渠道 {channel_id} 没有可用音色"
        voice_id = voices[0]["id"]
        print(f"[voices] ok -> {len(voices)} 个音色，首个: {voices[0]['name']} ({voice_id})")

    return channel_id, voice_id


def test_history(base_url: str):
    """获取历史记录"""
    url = f"{base_url.rstrip('/')}/api/v1/history"
    with httpx.Client(timeout=10.0, headers=AUTH_HEADERS) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()
        assert data.get("success") is True, f"history 响应异常: {data}"
        records = data.get("data", [])
        print(f"[history] ok -> {len(records)} 条记录")


def test_audio_stream(base_url: str):
    """流式回放历史音频"""
    history_url = f"{base_url.rstrip('/')}/api/v1/history"
    with httpx.Client(timeout=10.0, headers=AUTH_HEADERS) as client:
        resp = client.get(history_url)
        resp.raise_for_status()
        records = resp.json().get("data", [])
        if not records:
            print("[stream] 跳过（无历史记录）")
            return
        audio_id = records[0]["id"]
        stream_url = f"{base_url.rstrip('/')}/api/v1/audio/stream/{audio_id}"
        resp = client.get(stream_url)
        resp.raise_for_status()
        assert len(resp.content) > 0, "流式音频数据为空"
        print(f"[stream] ok -> audio_id={audio_id}, size={len(resp.content)} bytes")


def test_channel_crud(base_url: str):
    """渠道 CRUD 测试（创建 -> 更新 -> 删除）"""
    channels_url = f"{base_url.rstrip('/')}/api/v1/channels"
    with httpx.Client(timeout=10.0, headers=AUTH_HEADERS) as client:
        # 创建
        payload = {
            "name": "测试渠道-自动删除",
            "type": "openai",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test",
            "priority": 0,
        }
        resp = client.post(channels_url, json=payload)
        resp.raise_for_status()
        channel_id = resp.json()["data"]["id"]
        print(f"[channel-crud] 创建 ok -> {channel_id}")

        # 更新
        resp = client.put(f"{channels_url}/{channel_id}", json={"name": "测试渠道-已更新"})
        resp.raise_for_status()
        assert resp.json()["data"]["name"] == "测试渠道-已更新"
        print(f"[channel-crud] 更新 ok")

        # 获取单个
        resp = client.get(f"{channels_url}/{channel_id}")
        resp.raise_for_status()
        print(f"[channel-crud] 获取 ok")

        # 删除
        resp = client.delete(f"{channels_url}/{channel_id}")
        resp.raise_for_status()
        print(f"[channel-crud] 删除 ok")

        # 确认已删除
        resp = client.get(f"{channels_url}/{channel_id}")
        assert resp.status_code == 404, f"删除后应返回 404，实际: {resp.status_code}"
        print(f"[channel-crud] 确认删除 ok (404)")


def test_reading(base_url: str, text: str, speed: int, voice: str, out_dir: str):
    url = f"{base_url.rstrip('/')}/api/v1/tts/reading"
    data = {
        "speakText": text,
        "speakSpeed": str(speed),
    }
    if voice:
        data["voice"] = voice

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }

    with httpx.Client(timeout=60.0, headers=AUTH_HEADERS) as client:
        resp = client.post(url, data=data, headers=headers)
        resp.raise_for_status()
        assert len(resp.content) > 0, "阅读接口返回音频数据为空"
        audio_path = save_audio(resp.content, out_dir, "reading")
        print(f"[reading] ok -> {audio_path}")


def main():
    global AUTH_HEADERS
    args = parse_args()
    AUTH_HEADERS = {"Authorization": f"Bearer {args.api_key}"}
    print("开始测试...", time.strftime("%Y-%m-%d %H:%M:%S"))

    test_health(args.base_url)
    test_openai_audio_invalid_params(args.base_url)
    channel_id, voice_id = test_voices(args.base_url)
    test_openai_audio(args.base_url, args.text, args.voice, args.speed, args.out_dir)
    test_preview(args.base_url, args.text, args.out_dir, channel_id)
    test_history(args.base_url)
    test_audio_stream(args.base_url)
    test_channel_crud(args.base_url)
    test_reading(args.base_url, args.text, args.reading_speed, args.reading_voice, args.out_dir)

    print("\n全部测试通过", time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"测试失败: {exc}")
        sys.exit(1)
