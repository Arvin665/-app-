from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, or_, select

from app.api.deps import CurrentDevice, DbSession
from app.core.security import new_id
from app.models import PersonalInspiration
from app.schemas.inspiration import InspirationCreate, InspirationUpdate
from app.services.query_utils import apply_period_filter
from app.services.record_utils import (
    apply_payload,
    apply_soft_delete_scope,
    ensure_can_edit,
    get_record_or_404,
    log_operation,
    scope_condition,
    serialize_record,
)

router = APIRouter(prefix="/inspirations", tags=["个人灵感角"])


@router.get("")
def list_inspirations(
    db: DbSession,
    device: CurrentDevice,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    keyword: Optional[str] = None,
    inspiration_type: Optional[str] = None,
    record_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period_type: Optional[str] = Query(default=None, pattern=r"^(day|week|month|quarter|year)$"),
    period_value: Optional[str] = None,
):
    """个人灵感角完全按创建设备隔离，管理员调用也只能看到自己的记录。"""
    query = apply_soft_delete_scope(select(PersonalInspiration), PersonalInspiration).where(
        scope_condition(PersonalInspiration, device)
    )
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(PersonalInspiration.content.like(pattern), PersonalInspiration.tags.like(pattern)))
    if inspiration_type:
        query = query.where(PersonalInspiration.inspiration_type == inspiration_type)
    if record_date:
        query = query.where(func.date(PersonalInspiration.record_time) == record_date)
    if start_date:
        query = query.where(PersonalInspiration.record_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        # 结束日期按自然日包含当天 23:59:59。
        query = query.where(PersonalInspiration.record_time < datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
    query = apply_period_filter(query, PersonalInspiration.record_time, period_type, period_value)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.scalars(
        query.order_by(PersonalInspiration.record_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [serialize_record(record, device) for record in records],
        "total": total,
        "page": page,
        "page_size": page_size,
        "private_scope": device.device_id,
    }


@router.get("/{record_id}")
def get_inspiration(record_id: str, db: DbSession, device: CurrentDevice):
    return serialize_record(get_record_or_404(db, PersonalInspiration, record_id, device), device)


@router.post("", status_code=201)
def create_inspiration(body: InspirationCreate, db: DbSession, device: CurrentDevice, request: Request):
    record = PersonalInspiration(record_id=new_id(), creator_id=device.device_id, data_status=1)
    apply_payload(record, body.model_dump())
    db.add(record)
    log_operation(
        db,
        device.device_id,
        "add",
        "inspiration",
        record.record_id,
        {"inspiration_type": record.inspiration_type},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.patch("/{record_id}")
def update_inspiration(
    record_id: str,
    body: InspirationUpdate,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    record = get_record_or_404(db, PersonalInspiration, record_id, device)
    ensure_can_edit(record, device)
    changes = apply_payload(record, body.model_dump(exclude_unset=True))
    log_operation(
        db,
        device.device_id,
        "update",
        "inspiration",
        record.record_id,
        {"changed_fields": sorted(changes.keys())},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.delete("/{record_id}")
def delete_inspiration(record_id: str, db: DbSession, device: CurrentDevice, request: Request):
    record = get_record_or_404(db, PersonalInspiration, record_id, device)
    ensure_can_edit(record, device)
    record.data_status = 0
    log_operation(
        db,
        device.device_id,
        "delete",
        "inspiration",
        record.record_id,
        {"content_preview": record.content[:50]},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"record_id": record_id, "deleted": True, "recycle_days": 7}
