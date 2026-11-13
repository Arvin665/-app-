from typing import Literal, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentDevice, DbSession
from app.models import PersonalInspiration, PropertySale, TenancyLease, WorkLog
from app.services.record_utils import apply_payload, can_edit, log_operation, serialize_record

router = APIRouter(prefix="/batch", tags=["批量管理"])

MODULE_MODELS = {
    "sale": PropertySale,
    "lease": TenancyLease,
    "work": WorkLog,
    "inspiration": PersonalInspiration,
}


class BatchRequest(BaseModel):
    """桌面端批量操作统一请求，单次上限避免误选整库。"""

    module: Literal["sale", "lease", "work", "inspiration"]
    record_ids: list[str] = Field(min_length=1, max_length=500)


class BatchTagRequest(BatchRequest):
    tags: str = Field(min_length=1, max_length=255)
    mode: Literal["append", "replace"] = "append"


def normalize_tags(value: str) -> list[str]:
    """同时兼容中英文逗号，去空、去重并保持输入顺序。"""
    return list(dict.fromkeys(item.strip() for item in value.replace("，", ",").split(",") if item.strip()))


@router.post("/delete")
def batch_delete(body: BatchRequest, db: DbSession, device: CurrentDevice, request: Request):
    """逐条校验编辑权限；无权限记录不删除，并在响应中明确返回。"""
    model = MODULE_MODELS[body.module]
    deleted: list[str] = []
    denied: list[str] = []
    missing: list[str] = []
    records = db.scalars(select(model).where(model.record_id.in_(body.record_ids))).all()
    by_id = {record.record_id: record for record in records}
    for record_id in body.record_ids:
        record = by_id.get(record_id)
        if record is None or record.data_status != 1:
            missing.append(record_id)
            continue
        if not can_edit(record, device):
            denied.append(record_id)
            continue
        record.data_status = 0
        deleted.append(record_id)
    if deleted:
        log_operation(
            db,
            device.device_id,
            "delete",
            body.module,
            None,
            {"operation": "batch_delete", "record_ids": deleted},
            request.client.host if request.client else None,
        )
    db.commit()
    return {
        "module": body.module,
        "deleted": deleted,
        "denied": denied,
        "missing": missing,
        "deleted_count": len(deleted),
        "recycle_days": 7,
    }


@router.post("/tag")
def batch_tag(body: BatchTagRequest, db: DbSession, device: CurrentDevice, request: Request):
    """批量追加或替换标签，仍逐条执行创建人权限校验。"""
    model = MODULE_MODELS[body.module]
    incoming = normalize_tags(body.tags)
    tagged: list[str] = []
    denied: list[str] = []
    missing: list[str] = []
    records = db.scalars(select(model).where(model.record_id.in_(body.record_ids))).all()
    by_id = {record.record_id: record for record in records}
    for record_id in body.record_ids:
        record = by_id.get(record_id)
        if record is None or record.data_status != 1:
            missing.append(record_id)
            continue
        if not can_edit(record, device):
            denied.append(record_id)
            continue
        existing = normalize_tags(record.tags or "") if body.mode == "append" else []
        merged = existing + [tag for tag in incoming if tag not in existing]
        result = ",".join(merged)
        if len(result) > 255:
            # 超长标签不截断用户原始文字，交由前端提示改用更短标签。
            denied.append(record_id)
            continue
        apply_payload(record, {"tags": result})
        tagged.append(record_id)
    if tagged:
        log_operation(
            db,
            device.device_id,
            "update",
            body.module,
            None,
            {"operation": "batch_tag", "mode": body.mode, "tags": incoming, "record_ids": tagged},
            request.client.host if request.client else None,
        )
    db.commit()
    records = db.scalars(select(model).where(model.record_id.in_(tagged))).all() if tagged else []
    return {
        "module": body.module,
        "tagged": tagged,
        "denied": denied,
        "missing": missing,
        "tagged_count": len(tagged),
        "records": [serialize_record(record, device) for record in records],
    }
