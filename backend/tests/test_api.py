import os
from pathlib import Path
import json
import zipfile
import wave
from datetime import date, datetime, timedelta

# 测试必须在导入应用前设置环境变量，确保使用独立 SQLite 文件而不触碰开发数据库。
ARTIFACTS = Path(__file__).parent / "test_artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)
DB_FILE = ARTIFACTS / "test_api.db"
if DB_FILE.exists():
    DB_FILE.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{DB_FILE.as_posix()}"
os.environ["REDIS_URL"] = "redis://127.0.0.1:6399/0"
os.environ["AUTO_CREATE_TABLES"] = "true"
os.environ["BOOTSTRAP_INVITE_CODE"] = "246810"
os.environ["SENSITIVE_FIELD_KEY"] = "test-secret-key-with-sufficient-length"
os.environ["UPLOAD_DIR"] = str(ARTIFACTS / "uploads")
os.environ["PUBLIC_BASE_URL"] = "http://testserver"
os.environ["AI_PROVIDER"] = "auto"
# 测试不能因为开发机配置了真实 Key 而发起付费 API 调用。
os.environ["DEEPSEEK_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook, load_workbook  # noqa: E402
from io import BytesIO  # noqa: E402
from PIL import Image  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app, seed_bootstrap_admin_invite  # noqa: E402
from app.models import Device, InviteCode  # noqa: E402

ADMIN_ID = "a" * 32
MEMBER_ID = "b" * 32


def headers(device_id: str) -> dict[str, str]:
    return {"X-Device-ID": device_id}


def bind(client: TestClient, device_id: str, invite_code: str):
    response = client.post(
        "/api/v1/auth/bind",
        json={"invite_code": invite_code, "device_id": device_id, "device_name": "测试设备"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def upload_material(
    client: TestClient,
    device_id: str,
    module: str,
    file_name: str,
    content: bytes,
    content_type: str,
    record_id: str | None = None,
):
    data = {"module": module}
    if record_id:
        data["record_id"] = record_id
    response = client.post(
        "/api/v1/materials/upload",
        headers=headers(device_id),
        data=data,
        files={"file": (file_name, content, content_type)},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_existing_admin_disables_legacy_bootstrap_invite():
    temporary_admin_id = "c" * 32
    with TestClient(app):
        with SessionLocal() as db:
            existing_admin = db.scalar(
                select(Device).where(Device.role_level == 1, Device.status == 1)
            )
            created_temporary_admin = existing_admin is None
            if created_temporary_admin:
                db.add(
                    Device(
                        device_id=temporary_admin_id,
                        device_name="升级测试管理员",
                        invite_code="246810",
                        role_level=1,
                        bind_time=datetime.now(),
                        last_online_time=datetime.now(),
                        status=1,
                    )
                )
            invite = db.scalar(select(InviteCode).where(InviteCode.invite_code == "246810"))
            assert invite is not None
            original_status = invite.status
            original_max_use_count = invite.max_use_count
            invite.status = 1
            invite.max_use_count = 10
            db.commit()

        seed_bootstrap_admin_invite()

        with SessionLocal() as db:
            invite = db.scalar(select(InviteCode).where(InviteCode.invite_code == "246810"))
            assert invite is not None and invite.status == 0
            invite.status = original_status
            invite.max_use_count = original_max_use_count
            if created_temporary_admin:
                temporary_admin = db.get(Device, temporary_admin_id)
                if temporary_admin is not None:
                    db.delete(temporary_admin)
            db.commit()


def test_full_business_flow():
    with TestClient(app) as client:
        admin = bind(client, ADMIN_ID, "246810")
        assert admin["role_level"] == 1

        invite_response = client.post(
            "/api/v1/admin/invites",
            headers=headers(ADMIN_ID),
            json={"max_use_count": 2, "role_level": 2},
        )
        assert invite_response.status_code == 201, invite_response.text
        member_invite = invite_response.json()["invite_code"]
        member = bind(client, MEMBER_ID, member_invite)
        assert member["role_level"] == 2

        sale_payload = {
            "project_name": "陆家嘴中心",
            "district": "浦东-陆家嘴",
            "deal_date": "2026-11-12",
            "deal_total_price": "32000",
            "buyer": "测试买方",
            "commission_remark": "仅管理员可见佣金",
        }
        sale_response = client.post("/api/v1/sales", headers=headers(ADMIN_ID), json=sale_payload)
        assert sale_response.status_code == 201, sale_response.text
        sale = sale_response.json()
        assert sale["commission_remark"] == "仅管理员可见佣金"
        assert sale["archive"]["month"] == "2026-11"

        member_view = client.get(f"/api/v1/sales/{sale['record_id']}", headers=headers(MEMBER_ID))
        assert member_view.status_code == 200
        assert member_view.json()["commission_remark"] is None

        empty_sale = client.post("/api/v1/sales", headers=headers(ADMIN_ID), json={})
        assert empty_sale.status_code == 201, empty_sale.text
        assert empty_sale.json()["project_name"] == "待补充项目"
        assert empty_sale.json()["district"] == "待确认区域"

        text_content = "陆家嘴项目底层资料：交易总价3.2亿，买方为示例企业。".encode("utf-8")
        text_material = upload_material(
            client, ADMIN_ID, "sale", "陆家嘴底层资料.txt", text_content, "text/plain"
        )
        assert text_material["extraction_status"] == "extracted"
        assert "交易总价3.2亿" in text_material["extracted_text"]

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "交易清单"
        sheet.append(["项目", "总价"])
        sheet.append(["陆家嘴示例", 32000])
        xlsx_buffer = BytesIO()
        workbook.save(xlsx_buffer)
        xlsx_material = upload_material(
            client,
            ADMIN_ID,
            "sale",
            "交易清单.xlsx",
            xlsx_buffer.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        assert xlsx_material["extraction_status"] == "extracted"
        assert "陆家嘴示例" in xlsx_material["extracted_text"]

        image_buffer = BytesIO()
        Image.new("RGB", (32, 32), "white").save(image_buffer, format="PNG")
        image_material = upload_material(
            client, ADMIN_ID, "sale", "现场照片.png", image_buffer.getvalue(), "image/png"
        )
        assert image_material["extraction_status"] in {"stored", "unavailable"}
        assert image_material["thumbnail_url"]

        linked = client.post(
            f"/api/v1/materials/{text_material['material_id']}/link",
            headers=headers(ADMIN_ID),
            json={"record_id": sale["record_id"]},
        )
        assert linked.status_code == 200, linked.text
        assert linked.json()["record_id"] == sale["record_id"]

        material_list = client.get(
            "/api/v1/materials?module=sale&keyword=底层资料&page_size=20",
            headers=headers(ADMIN_ID),
        )
        assert material_list.status_code == 200, material_list.text
        assert any(item["material_id"] == text_material["material_id"] for item in material_list.json()["items"])
        member_material = client.get(
            f"/api/v1/materials/{text_material['material_id']}",
            headers=headers(MEMBER_ID),
        )
        assert member_material.status_code == 200
        assert "交易总价3.2亿" in member_material.json()["extracted_text"]

        disposable = upload_material(
            client, ADMIN_ID, "sale", "待删除.txt", "临时资料".encode("utf-8"), "text/plain"
        )
        deleted_material = client.delete(
            f"/api/v1/materials/{disposable['material_id']}", headers=headers(ADMIN_ID)
        )
        assert deleted_material.status_code == 200
        assert client.get(
            f"/api/v1/materials/{disposable['material_id']}", headers=headers(ADMIN_ID)
        ).status_code == 404

        forbidden_update = client.patch(
            f"/api/v1/sales/{sale['record_id']}",
            headers=headers(MEMBER_ID),
            json={"remark": "越权修改"},
        )
        assert forbidden_update.status_code == 403

        duplicate = client.post("/api/v1/sales", headers=headers(ADMIN_ID), json=sale_payload)
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["code"] == "DUPLICATE_RECORD"

        private_inspiration = client.post(
            "/api/v1/inspirations",
            headers=headers(ADMIN_ID),
            json={"record_time": "2026-11-12T10:00:00", "content": "管理员私有灵感"},
        )
        assert private_inspiration.status_code == 201, private_inspiration.text
        member_inspirations = client.get("/api/v1/inspirations", headers=headers(MEMBER_ID))
        assert member_inspirations.status_code == 200
        assert member_inspirations.json()["total"] == 0

        private_work = client.post(
            "/api/v1/work-logs",
            headers=headers(MEMBER_ID),
            json={"record_type": "每日心得", "record_date": "2026-11-12", "content": "成员私有记录"},
        )
        assert private_work.status_code == 201, private_work.text
        admin_work = client.get("/api/v1/work-logs", headers=headers(ADMIN_ID))
        assert admin_work.status_code == 200
        assert all(item["content"] != "成员私有记录" for item in admin_work.json()["items"])

        private_work_material = upload_material(
            client,
            MEMBER_ID,
            "work",
            "成员私有跟进.txt",
            "这条资料跟随私有工作记录隔离。".encode("utf-8"),
            "text/plain",
            private_work.json()["record_id"],
        )
        assert client.get(
            f"/api/v1/materials/{private_work_material['material_id']}", headers=headers(ADMIN_ID)
        ).status_code == 404

        shared_work = client.patch(
            f"/api/v1/work-logs/{private_work.json()['record_id']}",
            headers=headers(MEMBER_ID),
            json={"is_shared": 1},
        )
        assert shared_work.status_code == 200
        admin_work = client.get("/api/v1/work-logs", headers=headers(ADMIN_ID))
        assert any(item["content"] == "成员私有记录" for item in admin_work.json()["items"])
        assert client.get(
            f"/api/v1/materials/{private_work_material['material_id']}", headers=headers(ADMIN_ID)
        ).status_code == 200

        plan = client.post(
            "/api/v1/work-logs",
            headers=headers(MEMBER_ID),
            json={
                "record_type": "待办计划",
                "record_date": "2026-11-13",
                "ext_field_4": "17:30",
                "content": "整理陆家嘴客户清单",
            },
        )
        assert plan.status_code == 201, plan.text
        plan_id = plan.json()["record_id"]
        status_response = client.post(
            f"/api/v1/work-logs/{plan_id}/status",
            headers=headers(MEMBER_ID),
            json={"status": 2, "note": "已完成"},
        )
        assert status_response.status_code == 200
        assert status_response.json()["ext_field_5"] == 2

        archive = client.post(
            "/api/v1/work-logs/archive-daily",
            headers=headers(MEMBER_ID),
            json={"record_date": "2026-11-13", "insight": "今日节奏正常"},
        )
        assert archive.status_code == 200, archive.text
        assert archive.json()["plan_count"] == 1
        assert archive.json()["review"]["record_type"] == "每日复盘"
        locked = client.post(
            f"/api/v1/work-logs/{plan_id}/status",
            headers=headers(MEMBER_ID),
            json={"status": 1, "note": "尝试解锁"},
        )
        assert locked.status_code == 409

        delete_sale = client.delete(f"/api/v1/sales/{sale['record_id']}", headers=headers(ADMIN_ID))
        assert delete_sale.status_code == 200
        recycle = client.get("/api/v1/recycle?module=sale", headers=headers(ADMIN_ID))
        assert recycle.status_code == 200, recycle.text
        assert recycle.json()["total"] >= 1
        restored = client.post(f"/api/v1/recycle/sale/{sale['record_id']}/restore", headers=headers(ADMIN_ID))
        assert restored.status_code == 200, restored.text

        export_response = client.get("/api/v1/transfer/export/sale", headers=headers(MEMBER_ID))
        assert export_response.status_code == 200, export_response.text
        workbook = load_workbook(BytesIO(export_response.content), read_only=True)
        sheet = workbook.active
        headers_row = [cell.value for cell in next(sheet.iter_rows(max_row=1))]
        commission_index = headers_row.index("佣金备注")
        data_row = list(next(sheet.iter_rows(min_row=2, max_row=2)))[commission_index].value
        assert data_row is None

        preview = client.post(
            "/api/v1/transfer/import/preview/sale",
            headers=headers(MEMBER_ID),
            files={"file": ("sale.xlsx", export_response.content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert preview.status_code == 200, preview.text
        assert preview.json()["duplicate_count"] >= 1

        tagged = client.post(
            "/api/v1/batch/tag",
            headers=headers(ADMIN_ID),
            json={"module": "sale", "record_ids": [sale["record_id"]], "tags": "重点,复购"},
        )
        assert tagged.status_code == 200, tagged.text
        assert tagged.json()["tagged_count"] == 1

        sync_pull = client.get("/api/v1/sync/pull/sale", headers=headers(MEMBER_ID))
        assert sync_pull.status_code == 200
        assert sync_pull.json()["records"]

        backup = client.get("/api/v1/admin/backup", headers=headers(ADMIN_ID))
        assert backup.status_code == 200
        assert backup.headers["content-type"].startswith("application/zip")

        member_only_private = client.post(
            "/api/v1/work-logs",
            headers=headers(MEMBER_ID),
            json={"record_type": "每日心得", "record_date": "2026-11-13", "content": "备份不得包含的成员私有内容"},
        )
        assert member_only_private.status_code == 201
        member_private_inspiration = client.post(
            "/api/v1/inspirations",
            headers=headers(MEMBER_ID),
            json={"record_time": "2026-11-13T11:00:00", "content": "备份不得包含的成员私有灵感"},
        )
        assert member_private_inspiration.status_code == 201
        private_backup_material = upload_material(
            client,
            MEMBER_ID,
            "work",
            "备份排除的私有资料.txt",
            "成员私有资料不得进入管理员备份。".encode("utf-8"),
            "text/plain",
            member_only_private.json()["record_id"],
        )

        # 在隐私数据写入后重新生成备份，才能真实验证过滤范围。
        backup = client.get("/api/v1/admin/backup", headers=headers(ADMIN_ID))
        assert backup.status_code == 200
        with zipfile.ZipFile(BytesIO(backup.content)) as package:
            backup_names = package.namelist()
            assert any(name.startswith("uploads/materials/sale/") for name in backup_names)
            assert any(name.endswith(".thumb.jpg") for name in backup_names)

        # 备份接口不能借管理员身份绕过私有工作记录与个人灵感隔离。
        with zipfile.ZipFile(BytesIO(backup.content)) as package:
            backup_data = json.loads(package.read("database.json"))
        backup_work_contents = {row["content"] for row in backup_data["tables"]["biz_work_log"]}
        backup_inspiration_contents = {
            row["content"] for row in backup_data["tables"]["biz_personal_inspiration"]
        }
        backup_material_ids = {
            row["material_id"] for row in backup_data["tables"]["sys_material"]
        }
        assert text_material["material_id"] in backup_material_ids
        assert xlsx_material["material_id"] in backup_material_ids
        assert image_material["material_id"] in backup_material_ids
        assert private_backup_material["material_id"] not in backup_material_ids
        assert backup_data["version"] == 3
        assert "备份不得包含的成员私有内容" not in backup_work_contents
        assert "管理员私有灵感" in backup_inspiration_contents
        assert "备份不得包含的成员私有灵感" not in backup_inspiration_contents


def test_ai_command_updates_only_named_field():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ai/apply-command",
            headers=headers(ADMIN_ID),
            json={
                "module": "sale",
                "current_fields": {"project_name": "陆家嘴中心", "deal_total_price": "10000"},
                "command": "总价改成3.2亿",
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["fields"]["deal_total_price"] == "32000.00"
        assert result["fields"]["project_name"] == "陆家嘴中心"

        work_extract = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={"module": "work", "text": "明天10点整理客户清单"},
        )
        assert work_extract.status_code == 200, work_extract.text
        work_fields = work_extract.json()["fields"]
        assert work_fields["record_type"] == "待办计划"
        assert work_fields["ext_field_4"] == "10:00"
        assert work_fields["content"] == "整理客户清单"

        parsed_date = client.post(
            "/api/v1/ai/parse-field",
            headers=headers(ADMIN_ID),
            json={"module": "sale", "field": "deal_date", "text": "明天下午三点"},
        )
        assert parsed_date.status_code == 200, parsed_date.text
        assert parsed_date.json()["value"] == (date.today() + timedelta(days=1)).isoformat()

        parsed_time = client.post(
            "/api/v1/ai/parse-field",
            headers=headers(ADMIN_ID),
            json={"module": "work", "field": "ext_field_4", "text": "下午三点半"},
        )
        assert parsed_time.status_code == 200, parsed_time.text
        assert parsed_time.json()["value"] == "15:30"

        parsed_price = client.post(
            "/api/v1/ai/parse-field",
            headers=headers(ADMIN_ID),
            json={"module": "sale", "field": "deal_total_price", "text": "3.2亿"},
        )
        assert parsed_price.status_code == 200, parsed_price.text
        assert parsed_price.json()["value"] == "32000.00"

        parsed_status = client.post(
            "/api/v1/ai/parse-field",
            headers=headers(ADMIN_ID),
            json={"module": "sale", "field": "deal_status", "text": "已经签约"},
        )
        assert parsed_status.status_code == 200, parsed_status.text
        assert parsed_status.json()["value"] == "已签约"

        work_filter_records = [
            {"record_type": "每日心得", "record_date": "2025-01-10", "content": "DATE-FILTER-WORK-outside-a"},
            {"record_type": "每日心得", "record_date": "2025-02-15", "content": "DATE-FILTER-WORK-inside"},
            {"record_type": "每日心得", "record_date": "2025-03-10", "content": "DATE-FILTER-WORK-outside-b"},
        ]
        for payload in work_filter_records:
            created = client.post("/api/v1/work-logs", headers=headers(ADMIN_ID), json=payload)
            assert created.status_code == 201, created.text
        work_range = client.get(
            "/api/v1/work-logs?keyword=DATE-FILTER-WORK&start_date=2025-02-01&end_date=2025-02-28&page_size=100",
            headers=headers(ADMIN_ID),
        )
        assert work_range.status_code == 200, work_range.text
        work_items = work_range.json()["items"]
        assert [item["content"] for item in work_items] == ["DATE-FILTER-WORK-inside"]

        inspiration_filter_records = [
            "2025-01-10T10:00:00",
            "2025-02-15T23:59:59",
            "2025-03-10T10:00:00",
        ]
        for index, record_time in enumerate(inspiration_filter_records):
            created = client.post(
                "/api/v1/inspirations",
                headers=headers(ADMIN_ID),
                json={"record_time": record_time, "content": f"DATE-FILTER-INSP-{index}"},
            )
            assert created.status_code == 201, created.text
        inspiration_range = client.get(
            "/api/v1/inspirations?keyword=DATE-FILTER-INSP&start_date=2025-02-01&end_date=2025-02-28&page_size=100",
            headers=headers(ADMIN_ID),
        )
        assert inspiration_range.status_code == 200, inspiration_range.text
        inspiration_items = inspiration_range.json()["items"]
        assert [item["content"] for item in inspiration_items] == ["DATE-FILTER-INSP-1"]
        assert inspiration_items[0]["record_time"].startswith("2025-02-15T23:59:59")


def test_material_original_is_saved_before_extraction(monkeypatch, tmp_path):
    from app.api import materials as materials_api

    monkeypatch.setattr(materials_api.settings, "upload_dir", str(tmp_path))

    def fail_extraction(*args, **kwargs):
        raise RuntimeError("simulated extraction failure")

    monkeypatch.setattr(materials_api, "extract_material", fail_extraction)
    with TestClient(app, raise_server_exceptions=False) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/materials/upload",
            headers=headers(ADMIN_ID),
            data={"module": "sale"},
            files={"file": ("原件优先.txt", "必须保留的原件".encode("utf-8"), "text/plain")},
        )
        assert response.status_code == 500
        saved = [path for path in (tmp_path / "materials" / "sale").rglob("*") if path.is_file()]
        assert len(saved) == 1
        assert saved[0].read_text(encoding="utf-8") == "必须保留的原件"


def test_transcribe_endpoint_returns_real_engine_result(monkeypatch):
    from app.api import ai as ai_api

    captured = {}

    def fake_transcribe(content: bytes):
        if not content.startswith(b"RIFF"):
            raise ValueError("仅支持 WAV 录音")
        captured["size"] = len(content)
        return {"text": "上海写字楼买卖项目", "provider": "test-engine", "language": "zh-CN"}

    monkeypatch.setattr(ai_api, "transcribe_wav", fake_transcribe)
    audio = BytesIO()
    with wave.open(audio, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b"\x00\x00" * 1600)

    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/transcribe",
            headers=headers(ADMIN_ID),
            files={"file": ("dictation.wav", audio.getvalue(), "audio/wav")},
        )
        assert response.status_code == 200, response.text
        assert response.json()["text"] == "上海写字楼买卖项目"
        assert captured["size"] > 44

        invalid = client.post(
            "/api/v1/ai/transcribe",
            headers=headers(ADMIN_ID),
            files={"file": ("dictation.wav", b"not-a-wave-file" * 4, "audio/wav")},
        )
        assert invalid.status_code == 422


def test_transcribe_media_accepts_native_audio_formats(monkeypatch):
    from app.api import ai as ai_api

    captured = {}

    def fake_transcribe_media(content: bytes, suffix: str):
        captured["content"] = content
        captured["suffix"] = suffix
        return {
            "text": "原生录音已经识别",
            "provider": "test-ffmpeg-asr",
            "language": "zh-CN",
        }

    monkeypatch.setattr(ai_api, "transcribe_media", fake_transcribe_media)
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/transcribe-media",
            headers=headers(ADMIN_ID),
            files={"file": ("native-recording.m4a", b"native-audio-content", "audio/mp4")},
        )
        assert response.status_code == 200, response.text
        assert response.json()["text"] == "原生录音已经识别"
        assert captured == {"content": b"native-audio-content", "suffix": ".m4a"}


def test_ai_extract_uses_deepseek_corrected_text(monkeypatch):
    from app.api import ai as ai_api

    captured = {}

    monkeypatch.setattr(ai_api, "deepseek_configured", lambda: True)

    async def fake_extract(text, module, provider_note=""):
        captured.update({"text": text, "module": module, "provider_note": provider_note})
        return {
            "module": module,
            "fields": {"project_name": "陆家嘴中心", "deal_total_price": "32000.00"},
            "confidence": {"project_name": 0.98, "deal_total_price": 0.96},
            "missing_fields": [],
            "provider": "deepseek",
            "note": "已纠错并分类",
            "corrected_text": "陆家嘴中心项目总价三点二亿元。",
        }

    monkeypatch.setattr(ai_api, "extract_with_deepseek", fake_extract)
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={"module": "sale", "text": "陆家嘴中心项目总价3.2亿"},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["provider"] == "deepseek"
        assert result["corrected_text"] == "陆家嘴中心项目总价三点二亿元。"
        assert captured["module"] == "sale"
        assert captured["text"] == "陆家嘴中心项目总价3.2亿"


def test_ai_extract_keeps_local_result_when_deepseek_fails(monkeypatch):
    from app.api import ai as ai_api

    monkeypatch.setattr(ai_api, "deepseek_configured", lambda: True)

    async def failed_extract(text, module, provider_note=""):
        raise RuntimeError("simulated DeepSeek timeout")

    monkeypatch.setattr(ai_api, "extract_with_deepseek", failed_extract)
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={"module": "sale", "text": "陆家嘴项目总价3.2亿"},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["provider"] == "local-rule"
        assert result["fields"]["deal_total_price"] == "32000.00"
        assert result["corrected_text"] is None
        assert "DeepSeek 本次未成功" in result["note"]


def test_ai_extract_smart_lease_fields_and_end_date():
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={
                "module": "lease",
                "text": "某某公司在上海中心租赁了2000平方米，签了3年合约，2026年3月1日起租，给了3个月装修免租期，租金每天每平方米8元，净租金每天每平方米6.5元，你自己算下到期时间",
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        fields = result["fields"]
        assert fields["company_name"] == "某某公司"
        assert fields["new_project"] == "上海中心"
        assert fields["new_area"] == "2000"
        assert fields["lease_term"] == "3"
        assert fields["start_date"] == "2026-03-01"
        assert fields["rent_free_period"] == "3"
        assert fields["rent_price"] == "8"
        assert fields["ext_field_3"] == "6.5"
        assert fields["end_date"] == "2029-02-28"


def test_ai_extract_distinguishes_net_and_gross_rent_in_either_order():
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={
                "module": "lease",
                "text": "净租金每天每平方米6.5元，租金每天每平方米8元",
            },
        )
        assert response.status_code == 200, response.text
        fields = response.json()["fields"]
        assert fields["ext_field_3"] == "6.5"
        assert fields["rent_price"] == "8"


def test_ai_extract_local_fallback_handles_full_lease_dictation():
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={
                "module": "lease",
                "text": (
                    "有一家企业叫新湖期货的一家子公司营业部，在新上海国际大厦的17楼做一套240房的面积，"
                    "净租金3.5块钱，面价的话是5块钱，租期签了3年，三个月的免租金和装修期。"
                    "然后的话是2026年的12月1号起租的，帮我记录一下。"
                ),
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["provider"] == "local-rule"
        fields = result["fields"]
        assert fields["company_name"] == "新湖期货的一家子公司营业部"
        assert fields["new_project"] == "新上海国际大厦"
        assert fields["floor"] == "17楼"
        assert fields["new_area"] == "240"
        assert fields["ext_field_3"] == "3.5"
        assert fields["rent_price"] == "5"
        assert fields["lease_term"] == "3"
        assert fields["rent_free_period"] == "3"
        assert fields["start_date"] == "2026-12-01"
        assert fields["end_date"] == "2029-11-30"


def test_ai_extract_splits_continuous_plan_dictation():
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={
                "module": "work",
                "intent": "plans",
                "text": "明天上午十点整理客户清单，下午三点联系张总确认看房。后天提交租金测算，另外下周一提醒我给王总回电话。",
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()
        candidates = result["plan_candidates"]
        assert len(candidates) == 4
        assert [item["content"] for item in candidates] == [
            "整理客户清单",
            "联系张总确认看房",
            "提交租金测算",
            "给王总回电话",
        ]
        assert candidates[0]["ext_field_4"] == "10:00"
        assert candidates[1]["ext_field_4"] == "15:00"
        assert candidates[0]["record_date"] == (date.today() + timedelta(days=1)).isoformat()


def test_ai_extract_deepseek_plan_candidates(monkeypatch):
    from app.api import ai as ai_api

    captured = {}
    monkeypatch.setattr(ai_api, "deepseek_configured", lambda: True)

    async def fake_extract(text, module, provider_note="", intent="record"):
        captured.update({"text": text, "module": module, "intent": intent})
        return {
            "module": module,
            "fields": {"record_type": "待办计划", "record_date": "2026-11-18", "content": "整理客户清单"},
            "confidence": {"content": 0.96},
            "missing_fields": [],
            "provider": "deepseek",
            "note": "已拆分",
            "corrected_text": "整理客户清单",
            "plan_candidates": [
                {"content": "整理客户清单", "record_date": "2026-11-18", "ext_field_4": "10:00", "confidence": 0.96},
                {"content": "联系张总确认看房", "record_date": "2026-11-18", "ext_field_4": "15:00", "confidence": 0.93},
            ],
        }

    monkeypatch.setattr(ai_api, "extract_with_deepseek", fake_extract)
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/ai/extract",
            headers=headers(ADMIN_ID),
            data={"module": "work", "intent": "plans", "text": "整理客户清单，联系张总确认看房"},
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert captured["intent"] == "plans"
        assert len(result["plan_candidates"]) == 2
        assert result["plan_candidates"][1]["ext_field_4"] == "15:00"


def test_plan_normalization_corrects_relative_date_and_keeps_missing_times(monkeypatch):
    from app.services import ai_smart

    text = (
        "帮我做一个工作计划：明天上午10点半带创元期货复看房子；"
        "回公司之后处理开泰远景的材料事情，然后做回访；下午继续做我的APP开发。"
    )
    monkeypatch.setattr(ai_smart, "application_today", lambda: date(2026, 11, 17))
    local_candidates = ai_smart.plan_candidates_from_text(text, "plans")
    assert len(local_candidates) == 4
    assert local_candidates[0]["content"] == "带创元期货复看房子"
    assert all(item["record_date"] == "2026-11-18" for item in local_candidates)
    assert [item["ext_field_4"] for item in local_candidates[:1]] == ["10:30"]
    assert all(item["ext_field_4"] is None for item in local_candidates[1:])

    payload = {
        "fields": {"record_type": "待办计划", "content": local_candidates[0]["content"]},
        "confidence": {"content": 0.95},
        "plan_candidates": [
            {
                "content": item["content"],
                "record_date": "2026-11-17",
                "ext_field_4": item["ext_field_4"],
                "confidence": 0.9,
                "source_text": item["source_text"],
            }
            for item in local_candidates
        ],
    }
    normalized = ai_smart._normalize_ai_payload("work", payload, text, "plans")
    assert len(normalized["plan_candidates"]) == 4
    assert all(item["record_date"] == "2026-11-18" for item in normalized["plan_candidates"])
    assert normalized["fields"]["record_date"] == "2026-11-18"
    assert normalized["fields"]["ext_field_4"] == "10:30"


def test_work_log_batch_is_atomic_and_respects_archive_lock():
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        response = client.post(
            "/api/v1/work-logs/batch",
            headers=headers(ADMIN_ID),
            json={
                "items": [
                    {
                        "record_type": "待办计划",
                        "record_date": "2035-01-01",
                        "ext_field_4": "10:00",
                        "content": "批量计划一",
                    },
                    {
                        "record_type": "待办计划",
                        "record_date": "2035-01-01",
                        "content": "批量计划二",
                    },
                ]
            },
        )
        assert response.status_code == 201, response.text
        assert response.json()["count"] == 2
        assert [item["content"] for item in response.json()["items"]] == ["批量计划一", "批量计划二"]

        rejected = client.post(
            "/api/v1/work-logs/batch",
            headers=headers(ADMIN_ID),
            json={
                "items": [
                    {
                        "record_type": "待办计划",
                        "record_date": "2035-01-02",
                        "content": "不应保存的批量计划",
                    },
                    {
                        "record_type": "每日心得",
                        "record_date": "2035-01-02",
                        "content": "混入的普通记录",
                    },
                ]
            },
        )
        assert rejected.status_code == 422
        after_reject = client.get(
            "/api/v1/work-logs?record_date=2035-01-02&page_size=100",
            headers=headers(ADMIN_ID),
        )
        assert after_reject.json()["total"] == 0

        lock_date = "2035-01-03"
        seed = client.post(
            "/api/v1/work-logs",
            headers=headers(ADMIN_ID),
            json={"record_type": "待办计划", "record_date": lock_date, "content": "归档种子计划"},
        )
        assert seed.status_code == 201, seed.text
        archived = client.post(
            "/api/v1/work-logs/archive-daily",
            headers=headers(ADMIN_ID),
            json={"record_date": lock_date, "insight": "锁定测试"},
        )
        assert archived.status_code == 200, archived.text
        locked = client.post(
            "/api/v1/work-logs/batch",
            headers=headers(ADMIN_ID),
            json={
                "items": [
                    {"record_type": "待办计划", "record_date": lock_date, "content": "锁定后新增计划"},
                ]
            },
        )
        assert locked.status_code == 409
        after_lock = client.get(
            f"/api/v1/work-logs?record_date={lock_date}&page_size=100",
            headers=headers(ADMIN_ID),
        )
        assert all(item["content"] != "锁定后新增计划" for item in after_lock.json()["items"])


def test_workspace_links_search_context_and_signed_files():
    project = "环贸广场二期测试楼"
    with TestClient(app) as client:
        bind(client, ADMIN_ID, "246810")
        invite = client.post(
            "/api/v1/admin/invites",
            headers=headers(ADMIN_ID),
            json={"max_use_count": 2, "role_level": 2},
        )
        assert invite.status_code == 201, invite.text
        bind(client, MEMBER_ID, invite.json()["invite_code"])

        sale = client.post(
            "/api/v1/sales",
            headers=headers(ADMIN_ID),
            json={"project_name": project, "district": "徐汇-徐家汇", "deal_date": "2026-11-19"},
        )
        assert sale.status_code == 201, sale.text
        lease = client.post(
            "/api/v1/leases",
            headers=headers(ADMIN_ID),
            json={"company_name": "闭环测试企业", "new_project": "环贸广场二期", "lease_type": "新租"},
        )
        assert lease.status_code == 201, lease.text
        shared_work = client.post(
            "/api/v1/work-logs",
            headers=headers(MEMBER_ID),
            json={"record_type": "客户跟进", "record_date": "2026-11-19", "content": "环贸广场二期客户回访", "related_project": "环贸广场二期", "is_shared": 1},
        )
        assert shared_work.status_code == 201, shared_work.text

        context = client.get(
            f"/api/v1/workspace/records/sale/{sale.json()['record_id']}/context",
            headers=headers(MEMBER_ID),
        )
        assert context.status_code == 200, context.text
        suggestion_keys = {(item["module"], item["record_id"]) for item in context.json()["suggestions"]["items"]}
        assert ("lease", lease.json()["record_id"]) in suggestion_keys
        assert ("work", shared_work.json()["record_id"]) in suggestion_keys

        linked = client.post(
            "/api/v1/workspace/links",
            headers=headers(MEMBER_ID),
            json={"source_module": "sale", "source_record_id": sale.json()["record_id"], "target_module": "lease", "target_record_id": lease.json()["record_id"], "relation_type": "same_project", "note": "同一楼宇交易与租赁"},
        )
        assert linked.status_code == 200, linked.text
        assert linked.json()["created"] is True
        link_id = linked.json()["link"]["link_id"]

        context = client.get(
            f"/api/v1/workspace/records/sale/{sale.json()['record_id']}/context",
            headers=headers(MEMBER_ID),
        )
        assert context.json()["links"]["total"] == 1
        assert all(item["record_id"] != lease.json()["record_id"] for item in context.json()["suggestions"]["items"])

        material = upload_material(
            client,
            MEMBER_ID,
            "sale",
            "环贸广场尽调材料.txt",
            "环贸广场二期权属和租赁材料。".encode("utf-8"),
            "text/plain",
            sale.json()["record_id"],
        )
        search = client.get(
            "/api/v1/workspace/search?keyword=环贸广场", headers=headers(MEMBER_ID)
        )
        assert search.status_code == 200, search.text
        search_kinds = {(item["kind"], item["entity_id"]) for item in search.json()["items"]}
        assert ("record", sale.json()["record_id"]) in search_kinds
        assert ("material", material["material_id"]) in search_kinds

        signed = client.get(material["file_url"])
        assert signed.status_code == 200
        assert signed.content.decode("utf-8") == "环贸广场二期权属和租赁材料。"
        tampered = material["file_url"][:-1] + ("0" if material["file_url"][-1] != "0" else "1")
        assert client.get(tampered).status_code == 403
        raw_path = f"/uploads/materials/sale/{material['material_id']}/{material['material_id']}.txt"
        assert client.get(raw_path).status_code == 404

        private_work = client.post(
            "/api/v1/work-logs",
            headers=headers(MEMBER_ID),
            json={"record_type": "每日心得", "record_date": "2026-11-19", "content": "环贸广场二期私有判断", "related_project": "环贸广场二期", "is_shared": 0},
        )
        assert private_work.status_code == 201, private_work.text
        forbidden_link = client.post(
            "/api/v1/workspace/links",
            headers=headers(ADMIN_ID),
            json={"source_module": "sale", "source_record_id": sale.json()["record_id"], "target_module": "work", "target_record_id": private_work.json()["record_id"]},
        )
        assert forbidden_link.status_code == 404
        admin_search = client.get(
            "/api/v1/workspace/search?keyword=私有判断", headers=headers(ADMIN_ID)
        )
        assert all(item["entity_id"] != private_work.json()["record_id"] for item in admin_search.json()["items"])

        backup = client.get("/api/v1/admin/backup", headers=headers(ADMIN_ID))
        with zipfile.ZipFile(BytesIO(backup.content)) as package:
            backup_data = json.loads(package.read("database.json"))
        assert any(row["link_id"] == link_id for row in backup_data["tables"]["sys_record_link"])

        unlinked = client.delete(f"/api/v1/workspace/links/{link_id}", headers=headers(ADMIN_ID))
        assert unlinked.status_code == 200, unlinked.text
        assert client.get(f"/api/v1/workspace/links?module=sale&record_id={sale.json()['record_id']}", headers=headers(MEMBER_ID)).json()["total"] == 0
