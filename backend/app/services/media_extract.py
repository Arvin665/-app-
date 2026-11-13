from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings
from app.services.local_asr import transcribe_wav


class MediaExtractionUnavailable(RuntimeError):
    """当前运行环境缺少音视频转码或语音识别能力。"""


def ffmpeg_path() -> Path | None:
    configured = (settings.ffmpeg_binary or "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_file():
            return candidate
    discovered = shutil.which("ffmpeg")
    if discovered:
        return Path(discovered)
    try:
        import imageio_ffmpeg

        bundled = Path(imageio_ffmpeg.get_ffmpeg_exe())
        if bundled.is_file():
            return bundled
    except (ImportError, RuntimeError, OSError):
        pass
    return None


def media_status() -> dict:
    ffmpeg = ffmpeg_path()
    return {
        "available": bool(ffmpeg),
        "ffmpeg": str(ffmpeg) if ffmpeg else "",
        "mode": "local-ffmpeg",
    }


def _duration_seconds(stderr: str) -> float | None:
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 2)


def transcribe_media(content: bytes, suffix: str) -> dict:
    ffmpeg = ffmpeg_path()
    if ffmpeg is None:
        raise MediaExtractionUnavailable("未安装 ffmpeg，无法读取音频或视频音轨")
    safe_suffix = suffix.lower() if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix.lower()) else ".bin"

    with tempfile.TemporaryDirectory(prefix="asset-library-media-") as temp_dir:
        source = Path(temp_dir) / f"source{safe_suffix}"
        target = Path(temp_dir) / "audio.wav"
        source.write_bytes(content)
        command = [
            str(ffmpeg),
            "-nostdin",
            "-hide_banner",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-sample_fmt",
            "s16",
            str(target),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=settings.asr_timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("音视频转码超时，请缩短文件或转成较小格式") from exc
        stderr = result.stderr.decode("utf-8", errors="replace")
        if result.returncode != 0 or not target.is_file():
            detail = stderr.strip().splitlines()[-1] if stderr.strip() else "ffmpeg 转码失败"
            raise RuntimeError(f"音轨提取失败：{detail[:180]}")
        wav_content = target.read_bytes()

    transcription = transcribe_wav(wav_content)
    return {
        **transcription,
        "duration_seconds": _duration_seconds(stderr),
        "audio_format": "wav/16kHz/mono/16bit",
    }
