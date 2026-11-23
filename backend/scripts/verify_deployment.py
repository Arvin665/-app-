from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import uuid
import wave
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

WRITE_STATE = "write"
VERIFY_STATE = "verify"
DEFAULT_SPEECH_WAV = Path(
    "/app/models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09/test_wavs/zh.wav"
)


def headers(device_id: str) -> dict[str, str]:
    return {"X-Device-ID": device_id}


def text_fixture(marker: str) -> bytes:
    return f"部署持久化验收资料\nmarker={marker}\n交易总价3.2亿元。".encode("utf-8")


def font_path() -> Path:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
        Path(r"C:\Windows\Fonts\arialbd.ttf"),
        Path(r"C:\Windows\Fonts\msyhbd.ttc"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError("未找到用于 OCR 验收入口图片的字体")


def image_fixture(marker: str) -> bytes:
    image = Image.new("RGB", (1200, 620), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(font_path()), 68)
    small = ImageFont.truetype(str(font_path()), 44)
    draw.text((72, 90), "ASSET LIBRARY", font=font, fill="#16221f")
    draw.text((72, 220), "DEPLOYMENT OCR CHECK", font=small, fill="#16221f")
    draw.text((72, 330), marker[:32], font=small, fill="#16221f")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def silence_wav(seconds: float = 1.0) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buffer.getvalue()


def request_json(response: httpx.Response) -> dict:
    response.raise_for_status()
    return response.json()


def speech_fixture(path: Path | None) -> tuple[bytes, str]:
    candidate = path or DEFAULT_SPEECH_WAV
    if candidate.is_file():
        return candidate.read_bytes(), candidate.name
    return silence_wav(), "silence.wav"


def write_checkpoint(
    client: httpx.Client,
    base_url: str,
    invite_code: str,
    speech_wav: Path | None = None,
) -> dict:
    marker = f"DEPLOY-{uuid.uuid4().hex[:12]}"
    device_id = hashlib.sha256(f"asset-library-verifier:{marker}".encode()).hexdigest()[:32]
    bind = request_json(
        client.post(
            f"{base_url}/auth/bind",
            json={
                "invite_code": invite_code,
                "device_id": device_id,
                "device_name": "部署自动验收设备",
            },
        )
    )
    if bind.get("role_level") != 1:
        raise RuntimeError("首次部署邀请码没有绑定为管理员")

    capabilities = request_json(client.get(f"{base_url}/ai/capabilities", headers=headers(device_id)))
    required = {
        "ocr": capabilities.get("ocr", {}).get("available"),
        "asr": capabilities.get("asr", {}).get("available"),
        "ffmpeg": capabilities.get("media", {}).get("available"),
    }
    failed = [name for name, available in required.items() if not available]
    if failed:
        raise RuntimeError(f"容器识别能力未就绪：{', '.join(failed)}")

    sale = request_json(
        client.post(
            f"{base_url}/sales",
            headers=headers(device_id),
            json={
                "project_name": f"部署验收项目-{marker[-6:]}",
                "district": "浦东-陆家嘴",
                "deal_date": "2026-11-13",
                "remark": marker,
            },
        )
    )
    record_id = sale["record_id"]

    material = request_json(
        client.post(
            f"{base_url}/materials/upload",
            headers=headers(device_id),
            data={"module": "sale", "record_id": record_id, "title": f"持久化验收-{marker}"},
            files={"file": ("deployment-check.txt", text_fixture(marker), "text/plain")},
        )
    )
    if material.get("extraction_status") != "extracted" or marker not in material.get("extracted_text", ""):
        raise RuntimeError("文本原件上传后未完成正文提取")

    image = request_json(
        client.post(
            f"{base_url}/materials/upload",
            headers=headers(device_id),
            data={"module": "sale", "record_id": record_id, "title": f"OCR验收-{marker}"},
            files={"file": ("ocr-deployment-check.png", image_fixture(marker), "image/png")},
        )
    )
    if image.get("extraction_status") != "extracted":
        raise RuntimeError(f"图片 OCR 验收失败：{image.get('extraction_note')}")
    if "ASSET" not in image.get("extracted_text", "").upper():
        raise RuntimeError("图片 OCR 没有识别到预期文字")

    audio_content, audio_name = speech_fixture(speech_wav)
    transcription = request_json(
        client.post(
            f"{base_url}/ai/transcribe",
            headers=headers(device_id),
            files={"file": (audio_name, audio_content, "audio/wav")},
        )
    )
    if transcription.get("provider") in {"", "unavailable", None}:
        raise RuntimeError("语音识别端点没有返回可用引擎")
    if speech_wav is not None and not str(transcription.get("text") or "").strip():
        raise RuntimeError("真实中文语音没有转写出文字")

    media_transcription = request_json(
        client.post(
            f"{base_url}/ai/transcribe-media",
            headers=headers(device_id),
            files={"file": (f"native-{audio_name}", audio_content, "audio/wav")},
        )
    )
    if media_transcription.get("provider") in {"", "unavailable", None}:
        raise RuntimeError("ffmpeg 音频转写端点没有返回可用引擎")
    if speech_wav is not None and not str(media_transcription.get("text") or "").strip():
        raise RuntimeError("ffmpeg 真实中文语音没有转写出文字")

    health = request_json(client.get(f"{base_url}/health"))
    if health.get("database") != "ok" or health.get("redis") != "ok":
        raise RuntimeError(f"MySQL/Redis 健康检查失败：{health}")

    return {
        "base_url": base_url,
        "device_id": device_id,
        "record_id": record_id,
        "text_material_id": material["material_id"],
        "image_material_id": image["material_id"],
        "marker": marker,
        "asr_provider": transcription.get("provider"),
        "asr_text": transcription.get("text", ""),
        "capabilities": capabilities,
        "health": health,
    }


def verify_checkpoint(client: httpx.Client, state: dict) -> None:
    base_url = state["base_url"].rstrip("/")
    device_id = state["device_id"]
    header = headers(device_id)
    sale = request_json(client.get(f"{base_url}/sales/{state['record_id']}", headers=header))
    if sale.get("remark") != state["marker"]:
        raise RuntimeError("MySQL 重启后业务记录内容不一致")

    text_material = request_json(
        client.get(f"{base_url}/materials/{state['text_material_id']}", headers=header)
    )
    if state["marker"] not in text_material.get("extracted_text", ""):
        raise RuntimeError("MySQL 重启后文本资料正文丢失")

    image_material = request_json(
        client.get(f"{base_url}/materials/{state['image_material_id']}", headers=header)
    )
    original = client.get(image_material["file_url"])
    original.raise_for_status()
    if not original.content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("上传卷重启后图片原件丢失或损坏")

    health = request_json(client.get(f"{base_url}/health"))
    if health.get("database") != "ok" or health.get("redis") != "ok":
        raise RuntimeError(f"重启后 MySQL/Redis 健康检查失败：{health}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Docker/MySQL/Redis/OCR/ASR 与持久化真实验收")
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--invite-code", default="246810")
    parser.add_argument("--mode", choices=[WRITE_STATE, VERIFY_STATE], required=True)
    parser.add_argument("--state-file", type=Path, default=Path("deployment-state.json"))
    parser.add_argument("--speech-wav", type=Path, help="包含清晰中文语音的 WAV 文件")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    with httpx.Client(timeout=180.0, follow_redirects=True) as client:
        if args.mode == WRITE_STATE:
            state = write_checkpoint(client, base_url, args.invite_code, args.speech_wav)
            args.state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"result": "write_passed", **state}, ensure_ascii=False, indent=2))
        else:
            if not args.state_file.is_file():
                raise RuntimeError(f"验收状态文件不存在：{args.state_file}")
            state = json.loads(args.state_file.read_text(encoding="utf-8"))
            verify_checkpoint(client, state)
            print(json.dumps({"result": "restart_persistence_passed", "marker": state["marker"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"DEPLOYMENT_VERIFICATION_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
