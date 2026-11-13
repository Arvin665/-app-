from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy import select

from app.api.deps import CurrentDevice, DbSession
from app.models import PersonalInspiration, PropertySale, TenancyLease, WorkLog
from app.schemas.inspiration import InspirationCreate
from app.schemas.lease import TenancyLeaseCreate
from app.schemas.sale import PropertySaleCreate
from app.schemas.sync import SyncPullResponse, SyncPushRequest, SyncPushResponse
from app.schemas.work import WorkLogCreate
from app.services.cache import auth_cache
from app.services.record_utils import (
    MODULE_MODELS,
    apply_payload,
    can_edit,
    log_operation,
    scope_condition,
    serialize_record,
)

router = APIRouter(prefix="/sync", tags=["增量同步"])
SCHEMAS = {
    PropertySale: PropertySaleCreate,
    TenancyLease: TenancyLeaseCreate,
    WorkLog: WorkLogCreate,
    PersonalInspiration: InspirationCreate,
}


@router.post("/push", response_model=SyncPushResponse)
def push_offline_records(
    body: SyncPushRequest,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    """离线批量上传按最后更新时间覆盖；旧于服务端的记录跳过并回传冲突。"""
    if body.module not in MODULE_MODELS:
        raise HTTPException(status_code=422, detail="不支持的业务模块")
    model = MODULE_MODELS[body.module]
    schema = SCHEMAS[model]
    accepted: list[str] = []
    skipped: list[str] = []
    conflicts: list[str] = []
    now = datetime.now()
    max_client_time = now + timedelta(minutes=5)

    for item in body.records:
        raw = {key: value for key, value in item.data.items() if key not in {"archive", "can_edit"}}
        try:
            validated = schema(**raw)
        except ValidationError:
            conflicts.append(item.record_id)
            continue
        payload = validated.model_dump()
        existing = db.get(model, item.record_id)
        client_time = min(item.client_updated_at, max_client_time)
        if existing is not None:
            if existing.data_status != 1:
                conflicts.append(item.record_id)
                continue
            if not can_edit(existing, device):
                conflicts.append(item.record_id)
                continue
            if client_time <= existing.update_time:
                skipped.append(item.record_id)
                continue
            apply_payload(existing, payload)
            existing.update_time = client_time
            log_operation(
                db,
                device.device_id,
                "update",
                body.module,
                existing.record_id,
                {"operation": "offline_sync", "client_updated_at": client_time.isoformat()},
                request.client.host if request.client else None,
            )
        else:
            record = model(record_id=item.record_id, creator_id=device.device_id, data_status=1)
            apply_payload(record, payload)
            record.update_time = client_time
            db.add(record)
            log_operation(
                db,
                device.device_id,
                "add",
                body.module,
                item.record_id,
                {"operation": "offline_sync_create"},
                request.client.host if request.client else None,
            )
        accepted.append(item.record_id)

    db.commit()
    if accepted:
        auth_cache.set_sync_cursor(device.device_id, body.module, now.isoformat())
    return SyncPushResponse(
        module=body.module,
        accepted=accepted,
        skipped=skipped,
        conflicts=conflicts,
        server_time=now,
    )


@router.get("/pull/{module}", response_model=SyncPullResponse)
def pull_records(
    module: str,
    db: DbSession,
    device: CurrentDevice,
    since: Optional[datetime] = Query(default=None),
    limit: int = Query(default=5000, ge=1, le=10000),
):
    """桌面全量拉取不传 since；移动端传上次游标做增量拉取。"""
    if module not in MODULE_MODELS:
        raise HTTPException(status_code=422, detail="不支持的业务模块")
    model = MODULE_MODELS[module]
    now = datetime.now()
    query = select(model).where(model.data_status == 1)
    if model is WorkLog:
        query = query.where(scope_condition(WorkLog, device))
    elif model is PersonalInspiration:
        query = query.where(scope_condition(PersonalInspiration, device))
    if since:
        query = query.where(model.update_time > since)
    records = db.scalars(query.order_by(model.update_time.asc()).limit(limit)).all()
    auth_cache.set_sync_cursor(device.device_id, module, now.isoformat())
    return SyncPullResponse(
        module=module,
        records=[serialize_record(record, device) for record in records],
        server_time=now,
    )


@router.get("/status")
def sync_status(device: CurrentDevice):
    """返回各模块最近同步游标；Redis 不可用时为空，不影响客户端自行保存游标。"""
    return {
        "device_id": device.device_id,
        "cursors": {
            module: auth_cache.get_sync_cursor(device.device_id, module)
            for module in ["sale", "lease", "work", "inspiration"]
        },
    }
