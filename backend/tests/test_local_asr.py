from array import array

from app.services import local_asr
from app.services.llm_extract import _normalize_payload


def test_transcribe_wav_falls_back_to_next_engine(monkeypatch):
    monkeypatch.setattr(local_asr, "provider_candidates", lambda: ["windows-speech", "vosk"])
    monkeypatch.setattr(
        local_asr,
        "_transcribe_windows_wav",
        lambda content: {"text": "", "provider": "windows-speech", "language": "zh-CN"},
    )
    monkeypatch.setattr(
        local_asr,
        "_transcribe_vosk_wav",
        lambda content: {"text": "上海写字楼成交", "provider": "vosk", "language": "zh-CN"},
    )

    result = local_asr.transcribe_wav(b"RIFF-test")

    assert result["text"] == "上海写字楼成交"
    assert result["provider"] == "vosk"


def test_transcribe_wav_skips_failed_engine_and_reports_empty_diagnostic(monkeypatch):
    def failed_windows(content):
        raise RuntimeError("engine crashed")

    monkeypatch.setattr(local_asr, "provider_candidates", lambda: ["windows-speech", "vosk"])
    monkeypatch.setattr(local_asr, "_transcribe_windows_wav", failed_windows)
    monkeypatch.setattr(
        local_asr,
        "_transcribe_vosk_wav",
        lambda content: {"text": "", "provider": "vosk", "language": "zh-CN"},
    )

    result = local_asr.transcribe_wav(b"RIFF-test")

    assert result["text"] == ""
    assert "engine crashed" in result["diagnostic"]


def test_pcm16_resample_changes_length():
    samples = array("h", [0, 1000, -1000, 0])

    result = local_asr._resample_pcm16(samples, source_rate=48000, target_rate=16000)

    assert len(result) == max(1, round(len(samples) * 16000 / 48000))


def test_deepseek_payload_filters_unknown_fields_and_builds_missing_fields():
    result = _normalize_payload(
        "sale",
        {
            "corrected_text": "浦东陆家嘴项目正在洽谈。",
            "fields": {"project_name": "陆家嘴项目", "not_a_field": "应被丢弃"},
            "confidence": {"project_name": 0.91, "not_a_field": 0.99},
            "note": "请核对日期",
        },
    )

    assert result["provider"] == "deepseek"
    assert result["fields"] == {"project_name": "陆家嘴项目"}
    assert result["confidence"] == {"project_name": 0.91}
    assert result["missing_fields"] == []
    assert result["corrected_text"] == "浦东陆家嘴项目正在洽谈。"
