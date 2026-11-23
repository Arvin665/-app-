from datetime import date

from app.services import ai_smart
from app.services.ai_extract import parse_date


def test_chinese_weekday_qualifiers_use_natural_week_semantics():
    today = date(2026, 11, 23)  # Monday

    assert parse_date("本周三上午十点", today=today)[0] == "2026-11-25"
    assert parse_date("这周三上午十点", today=today)[0] == "2026-11-25"
    assert parse_date("周三上午十点", today=today)[0] == "2026-11-25"
    assert parse_date("下周三上午十点", today=today)[0] == "2026-12-02"
    assert parse_date("下个星期三上午十点", today=today)[0] == "2026-12-02"
    assert parse_date("下下周三上午十点", today=today)[0] == "2026-12-09"


def test_next_week_date_overrides_model_date_and_keeps_time(monkeypatch):
    text = "联系创元期货的附加下周三上午的十点钟"
    monkeypatch.setattr(ai_smart, "application_today", lambda: date(2026, 11, 23))

    local_candidates = ai_smart.plan_candidates_from_text(text, "plans")
    assert len(local_candidates) == 1
    assert local_candidates[0]["record_date"] == "2026-12-02"
    assert local_candidates[0]["ext_field_4"] == "10:00"

    payload = {
        "fields": {
            "record_type": "待办计划",
            "record_date": "2026-11-25",
            "content": local_candidates[0]["content"],
        },
        "confidence": {"content": 0.95, "record_date": 0.75},
        "plan_candidates": [
            {
                **local_candidates[0],
                "record_date": "2026-11-25",
            }
        ],
    }
    normalized = ai_smart._normalize_ai_payload("work", payload, text, "plans")

    assert len(normalized["plan_candidates"]) == 1
    assert normalized["plan_candidates"][0]["record_date"] == "2026-12-02"
    assert normalized["plan_candidates"][0]["ext_field_4"] == "10:00"
    assert normalized["fields"]["record_date"] == "2026-12-02"
