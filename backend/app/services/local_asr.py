import json
import os
import platform
import subprocess
import tempfile
import threading
import wave
from array import array
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from app.core.config import settings


class LocalAsrUnavailable(RuntimeError):
    """本机没有可用的中文离线语音识别引擎。"""


_vosk_model = None
_vosk_lock = threading.Lock()
_sense_voice_recognizer = None
_sense_voice_lock = threading.Lock()


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


def default_sense_voice_model_path() -> Path:
    models_dir = Path(__file__).resolve().parents[2] / "models"
    # 新版本优先；旧环境仍保留 2024-07-17 模型的机器继续可用。
    for name in (
        "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09",
        "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17",
    ):
        candidate = models_dir / name
        if candidate.is_dir():
            return candidate
    return models_dir / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09"


def vosk_model_path() -> Path | None:
    candidate = (
        Path(settings.vosk_model_path).expanduser()
        if settings.vosk_model_path
        else default_vosk_model_path()
    )
    if candidate.is_dir() and (candidate / "conf" / "model.conf").is_file():
        return candidate
    return None


def sense_voice_model_path() -> Path | None:
    candidate = (
        Path(settings.sense_voice_model_path).expanduser()
        if settings.sense_voice_model_path
        else default_sense_voice_model_path()
    )
    if (candidate / "model.int8.onnx").is_file() and (candidate / "tokens.txt").is_file():
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


def sense_voice_available() -> bool:
    if sense_voice_model_path() is None:
        return False
    try:
        import sherpa_onnx  # noqa: F401
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


def provider_candidates() -> list[str]:
    requested = (settings.asr_engine or "auto").strip().lower()
    providers = {
        "sensevoice": sense_voice_available,
        "windows-speech": windows_speech_available,
        "vosk": vosk_available,
    }
    if requested in {"sensevoice", "sherpa-onnx"}:
        return ["sensevoice"] if providers["sensevoice"]() else []
    if requested in providers:
        return [requested] if providers[requested]() else []
    return [provider for provider in ("sensevoice", "windows-speech", "vosk") if providers[provider]()]


def selected_provider() -> str | None:
    candidates = provider_candidates()
    return candidates[0] if candidates else None


def local_asr_status() -> dict:
    provider = selected_provider()
    return {
        "available": bool(provider),
        "provider": provider or "unavailable",
        "mode": "local-offline" if provider else "not-configured",
        "language": "zh-CN",
        "requested_engine": settings.asr_engine,
        "providers": {
            "sensevoice": sense_voice_available(),
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


def _load_sense_voice_recognizer():
    global _sense_voice_recognizer
    if _sense_voice_recognizer is not None:
        return _sense_voice_recognizer
    model_path = sense_voice_model_path()
    if model_path is None:
        raise LocalAsrUnavailable("SenseVoiceSmall 模型目录未配置或不存在")
    try:
        import sherpa_onnx
    except ImportError as exc:
        raise LocalAsrUnavailable("当前后台没有安装 Sherpa-ONNX 语音识别运行时") from exc
    with _sense_voice_lock:
        if _sense_voice_recognizer is None:
            _sense_voice_recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
                model=str(model_path / "model.int8.onnx"),
                tokens=str(model_path / "tokens.txt"),
                num_threads=2,
                use_itn=True,
                language="zh",
                provider="cpu",
            )
    return _sense_voice_recognizer


def _resample_pcm16(samples: array, source_rate: int, target_rate: int = 16000) -> array:
    if source_rate == target_rate or not samples:
        return samples
    target_length = max(1, round(len(samples) * target_rate / source_rate))
    result = array("h")
    ratio = source_rate / target_rate
    for index in range(target_length):
        position = index * ratio
        left = min(int(position), len(samples) - 1)
        right = min(left + 1, len(samples) - 1)
        fraction = position - left
        value = samples[left] * (1 - fraction) + samples[right] * fraction
        result.append(max(-32768, min(32767, int(value))))
    return result


def _transcribe_sense_voice_wav(content: bytes) -> dict:
    if not content.startswith(b"RIFF"):
        raise ValueError("仅支持 WAV 录音")
    with wave.open(BytesIO(content), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
            raise ValueError("SenseVoiceSmall 仅接受 16 位单声道 WAV")
        sample_rate = audio.getframerate()
        samples = array("h")
        samples.frombytes(audio.readframes(audio.getnframes()))
    samples = _resample_pcm16(samples, sample_rate)
    if not samples:
        return {"text": "", "provider": "sensevoice", "language": "zh-CN"}
    recognizer = _load_sense_voice_recognizer()
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, [sample / 32768.0 for sample in samples])
    recognizer.decode_stream(stream)
    result = stream.result
    text = str(getattr(result, "text", "") or "").strip()
    return {
        "text": text,
        "provider": "sensevoice",
        "language": "zh-CN",
    }


def transcribe_wav(content: bytes) -> dict:
    if not content.startswith(b"RIFF"):
        raise ValueError("仅支持 WAV 录音")
    providers = provider_candidates()
    if not providers:
        raise LocalAsrUnavailable("当前后台没有配置中文语音识别引擎")

    last_empty: dict | None = None
    failures: list[Exception] = []
    for provider in providers:
        try:
            if provider == "sensevoice":
                result = _transcribe_sense_voice_wav(content)
            elif provider == "windows-speech":
                result = _transcribe_windows_wav(content)
            else:
                result = _transcribe_vosk_wav(content)
            if str(result.get("text") or "").strip():
                return result
            last_empty = result
        except (ValueError, TimeoutError):
            raise
        except Exception as exc:
            failures.append(exc)

    if last_empty is not None:
        if failures:
            last_empty["diagnostic"] = "；".join(str(error) for error in failures)[-600:]
        return last_empty
    if len(failures) == 1:
        raise RuntimeError(str(failures[0])) from failures[0]
    if failures:
        detail = "；".join(str(error) for error in failures)[-600:]
        raise RuntimeError(f"所有本地语音引擎均识别失败：{detail}") from failures[-1]
    raise LocalAsrUnavailable("当前后台没有配置中文语音识别引擎")
