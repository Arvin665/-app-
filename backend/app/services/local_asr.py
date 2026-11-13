import json
import os
import platform
import subprocess
import tempfile
import threading
import wave
from functools import lru_cache
from pathlib import Path

from app.core.config import settings


class LocalAsrUnavailable(RuntimeError):
    """本机没有可用的中文离线语音识别引擎。"""


_vosk_model = None
_vosk_lock = threading.Lock()


def powershell_path() -> Path | None:
    if platform.system() != "Windows":
        return None
    windows_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    candidates = [
        windows_root / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
        windows_root / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe",
    ]
    return next((path for path in candidates if path.is_file()), None)


def recognizer_script_path() -> Path:
    return Path(__file__).resolve().parents[2] / "scripts" / "recognize_zh.ps1"


def default_vosk_model_path() -> Path:
    return Path(__file__).resolve().parents[2] / "models" / "vosk-model-small-cn-0.22"


def vosk_model_path() -> Path | None:
    candidate = (
        Path(settings.vosk_model_path).expanduser()
        if settings.vosk_model_path
        else default_vosk_model_path()
    )
    if candidate.is_dir() and (candidate / "conf" / "model.conf").is_file():
        return candidate
    return None


def vosk_available() -> bool:
    if vosk_model_path() is None:
        return False
    try:
        import vosk  # noqa: F401
    except ImportError:
        return False
    return True


def windows_speech_available() -> bool:
    if not powershell_path() or not recognizer_script_path().is_file():
        return False
    return windows_recognizer_check() is not None


@lru_cache(maxsize=1)
def windows_recognizer_check() -> dict[str, str] | None:
    """Only report Windows Speech as available after loading a Chinese recognizer."""
    powershell = powershell_path()
    script = recognizer_script_path()
    if not powershell or not script.is_file():
        return None
    command = [
        str(powershell),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-CheckOnly",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    lines = [
        line for line in result.stdout.decode("utf-8", errors="replace").splitlines() if line.strip()
    ]
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    if payload.get("available") is not True or payload.get("culture") != "zh-CN":
        return None
    return {
        "engine": str(payload.get("engine") or "Windows Speech"),
        "culture": "zh-CN",
    }


def selected_provider() -> str | None:
    requested = (settings.asr_engine or "auto").strip().lower()
    providers = {
        "windows-speech": windows_speech_available,
        "vosk": vosk_available,
    }
    if requested in providers:
        return requested if providers[requested]() else None
    for provider in ("windows-speech", "vosk"):
        if providers[provider]():
            return provider
    return None


def local_asr_status() -> dict:
    provider = selected_provider()
    return {
        "available": bool(provider),
        "provider": provider or "unavailable",
        "mode": "local-offline" if provider else "not-configured",
        "language": "zh-CN",
        "requested_engine": settings.asr_engine,
        "providers": {
            "windows-speech": windows_speech_available(),
            "vosk": vosk_available(),
        },
    }


def _transcribe_windows_wav(content: bytes) -> dict:
    if not content.startswith(b"RIFF"):
        raise ValueError("仅支持 WAV 录音")
    powershell = powershell_path()
    script = recognizer_script_path()
    if not powershell or not script.is_file():
        raise LocalAsrUnavailable("当前后台没有配置中文语音识别引擎")

    with tempfile.TemporaryDirectory(prefix="asset-library-asr-") as temp_dir:
        audio_path = Path(temp_dir) / "dictation.wav"
        audio_path.write_bytes(content)
        command = [
            str(powershell),
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-AudioPath",
            str(audio_path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                timeout=settings.asr_timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError("语音识别超时，请缩短录音后重试") from exc

    stdout = result.stdout.decode("utf-8", errors="replace").strip()
    stderr = result.stderr.decode("utf-8", errors="replace").strip()
    if result.returncode != 0:
        if "NO_ZH_RECOGNIZER" in stderr or "NO_ZH_RECOGNIZER" in stdout:
            raise LocalAsrUnavailable("Windows 未安装中文离线语音识别组件")
        raise RuntimeError(stderr or stdout or "本地语音识别失败")

    lines = [line for line in stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("本地语音识别没有返回结果")
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError("本地语音识别返回格式异常") from exc
    return {
        "text": str(payload.get("text") or "").strip(),
        "provider": "windows-speech",
        "language": str(payload.get("culture") or "zh-CN"),
    }


def _load_vosk_model():
    global _vosk_model
    if _vosk_model is not None:
        return _vosk_model
    model_path = vosk_model_path()
    if model_path is None:
        raise LocalAsrUnavailable("Vosk 中文模型目录未配置或不存在")
    try:
        from vosk import Model, SetLogLevel
    except ImportError as exc:
        raise LocalAsrUnavailable("当前后台没有安装 Vosk 语音识别引擎") from exc
    with _vosk_lock:
        if _vosk_model is None:
            SetLogLevel(-1)
            _vosk_model = Model(str(model_path))
    return _vosk_model


def _transcribe_vosk_wav(content: bytes) -> dict:
    try:
        from vosk import KaldiRecognizer
    except ImportError as exc:
        raise LocalAsrUnavailable("当前后台没有安装 Vosk 语音识别引擎") from exc
    model = _load_vosk_model()
    from io import BytesIO

    with wave.open(BytesIO(content), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("Vosk 仅接受 16 位单声道 WAV")
        sample_rate = audio.getframerate()
        recognizer = KaldiRecognizer(model, sample_rate)
        recognizer.SetWords(False)
        segments: list[str] = []
        while True:
            data = audio.readframes(4000)
            if not data:
                break
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if result.get("text"):
                    segments.append(str(result["text"]).replace(" ", ""))
        final = json.loads(recognizer.FinalResult())
        if final.get("text"):
            segments.append(str(final["text"]).replace(" ", ""))
    return {
        "text": "".join(segments).strip(),
        "provider": "vosk",
        "language": "zh-CN",
    }


def transcribe_wav(content: bytes) -> dict:
    if not content.startswith(b"RIFF"):
        raise ValueError("仅支持 WAV 录音")
    provider = selected_provider()
    if provider == "windows-speech":
        return _transcribe_windows_wav(content)
    if provider == "vosk":
        return _transcribe_vosk_wav(content)
    raise LocalAsrUnavailable("当前后台没有配置中文语音识别引擎")
