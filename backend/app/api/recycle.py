from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import or_, select

from app.api.deps import CurrentDevice, DbSession
from app.models import PersonalInspiration, PropertySale, TenancyLease, WorkLog
from app.services.record_utils import (
    MODULE_MODELS,
    MODULE_NAMES,
    RECYCLE_DAYS,
    can_edit,
    log_operation,
    serialize_record,
)

router = APIRouter(prefix="/recycle", tags=["回收站"])


def visible_deleted_condition(model, device):
    """回收站沿用业务隔离：成员看本人，管理员看团队共享；灵感始终仅本人。"""
    if model is PersonalInspiration:
        return model.creator_id == device.device_id
    if model is WorkLog:
        if device.role_level == 1:
            return or_(model.creator_id == device.device_id, model.is_shared == 1)
        return model.creator_id == device.device_id
    if device.role_level == 1:
        return True
    return model.creator_id == device.device_id


@router.get("")
def list_recycle_bin(
    db: DbSession,
    device: CurrentDevice,
    module: Optional[str] = Query(default=None, pattern=r"^(sale|lease|work|inspiration)$"),
):
    """只展示 7 天内软删除数据，不提供物理销毁入口。"""
    cutoff = datetime.now() - timedelta(days=RECYCLE_DAYS)
    modules = [module] if module else list(MODULE_MODELS.keys())
    result = []
    for module_name in modules:
        model = MODULE_MODELS[module_name]
        records = db.scalars(
            select(model)
            .where(model.data_status == 0, model.update_time >= cutoff, visible_deleted_condition(model, device))
            .order_by(model.update_time.desc())
            .limit(500)
        ).all()
        for record in records:
            item = serialize_record(record, device)
            item["can_restore"] = can_edit(record, device, include_deleted=True)
            item["deleted_at"] = record.update_time.isoformat()
            item["recycle_expires_at"] = (record.update_time + timedelta(days=RECYCLE_DAYS)).isoformat()
            result.append({"module": module_name, "module_name": MODULE_NAMES[module_name], "record": item})
    result.sort(key=lambda item: item["record"]["deleted_at"], reverse=True)
    return {"items": result, "total": len(result), "retention_days": RECYCLE_DAYS}


@router.post("/{module}/{record_id}/restore")
def restore_record(
    module: str,
    record_id: str,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    if module not in MODULE_MODELS:
        raise HTTPException(status_code=422, detail="不支持的业务模块")
    model = MODULE_MODELS[module]
    record = db.get(model, record_id)
    if record is None or record.data_status != 0:
        raise HTTPException(status_code=404, detail="回收站中不存在该记录")
    if record.update_time < datetime.now() - timedelta(days=RECYCLE_DAYS):
        raise HTTPException(status_code=410, detail="记录已超过 7 天恢复窗口")
    if not can_edit(record, device, include_deleted=True):
        raise HTTPException(status_code=403, detail="无权恢复该记录")
    record.data_status = 1
    record.update_time = datetime.now()
    log_operation(
        db,
        device.device_id,
        "update",
        module,
        record.record_id,
        {"operation": "restore"},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return {"restored": True, "module": module, "record": serialize_record(record, device)}
