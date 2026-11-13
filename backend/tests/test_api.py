import os
from pathlib import Path
import json
import zipfile

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

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import load_workbook  # noqa: E402
from io import BytesIO  # noqa: E402

from app.main import app  # noqa: E402

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

        shared_work = client.patch(
            f"/api/v1/work-logs/{private_work.json()['record_id']}",
            headers=headers(MEMBER_ID),
            json={"is_shared": 1},
        )
        assert shared_work.status_code == 200
        admin_work = client.get("/api/v1/work-logs", headers=headers(ADMIN_ID))
        assert any(item["content"] == "成员私有记录" for item in admin_work.json()["items"])

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

        # 在隐私数据写入后重新生成备份，才能真实验证过滤范围。
        backup = client.get("/api/v1/admin/backup", headers=headers(ADMIN_ID))
        assert backup.status_code == 200

        # 备份接口不能借管理员身份绕过私有工作记录与个人灵感隔离。
        with zipfile.ZipFile(BytesIO(backup.content)) as package:
            backup_data = json.loads(package.read("database.json"))
        backup_work_contents = {row["content"] for row in backup_data["tables"]["biz_work_log"]}
        backup_inspiration_contents = {
            row["content"] for row in backup_data["tables"]["biz_personal_inspiration"]
        }
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
