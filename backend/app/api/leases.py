from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import case, func, or_, select

from app.api.deps import CurrentDevice, DbSession
from app.core.security import new_id
from app.models import TenancyLease
from app.schemas.lease import TenancyLeaseCreate, TenancyLeaseUpdate
from app.services.query_utils import apply_period_filter
from app.services.record_utils import (
    apply_payload,
    apply_soft_delete_scope,
    duplicate_detail,
    ensure_can_edit,
    find_duplicates,
    get_record_or_404,
    log_operation,
    serialize_record,
)

router = APIRouter(prefix="/leases", tags=["企业租赁信息"])


def duplicate_conflict(duplicates: list[TenancyLease]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "DUPLICATE_RECORD", "message": "发现重复企业租赁记录", "duplicates": duplicate_detail(duplicates)},
    )


@router.get("")
def list_leases(
    db: DbSession,
    device: CurrentDevice,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    keyword: Optional[str] = None,
    company_name: Optional[str] = None,
    new_project: Optional[str] = None,
    industry: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period_type: Optional[str] = Query(default=None, pattern=r"^(day|week|month|quarter|year)$"),
    period_value: Optional[str] = None,
):
    """团队共享租赁库，支持企业、楼宇、行业与时间筛选。"""
    query = apply_soft_delete_scope(select(TenancyLease), TenancyLease)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(
            or_(
                TenancyLease.company_name.like(pattern),
                TenancyLease.new_project.like(pattern),
                TenancyLease.old_project.like(pattern),
                TenancyLease.move_reason.like(pattern),
                TenancyLease.remark.like(pattern),
            )
        )
    if company_name:
        query = query.where(TenancyLease.company_name.like(f"%{company_name.strip()}%"))
    if new_project:
        query = query.where(TenancyLease.new_project.like(f"%{new_project.strip()}%"))
    if industry:
        query = query.where(TenancyLease.industry.like(f"%{industry.strip()}%"))
    if start_date:
        query = query.where(TenancyLease.start_date >= start_date)
    if end_date:
        query = query.where(TenancyLease.start_date <= end_date)
    query = apply_period_filter(query, TenancyLease.start_date, period_type, period_value)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.scalars(
        query.order_by(
            case((TenancyLease.start_date.is_(None), 1), else_=0),
            TenancyLease.start_date.desc(),
            TenancyLease.update_time.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [serialize_record(record, device) for record in records],
        "total": total,
        "page": page,
        "page_size": page_size,
        "module": "lease",
    }


@router.get("/{record_id}")
def get_lease(record_id: str, db: DbSession, device: CurrentDevice):
    return serialize_record(get_record_or_404(db, TenancyLease, record_id, device), device)


@router.post("", status_code=201)
def create_lease(
    body: TenancyLeaseCreate,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    force: bool = False,
):
    payload = body.model_dump()
    duplicates = find_duplicates(db, TenancyLease, payload)
    if duplicates and not force:
        raise duplicate_conflict(duplicates)
    record = TenancyLease(record_id=new_id(), creator_id=device.device_id, data_status=1)
    apply_payload(record, payload)
    db.add(record)
    log_operation(
        db,
        device.device_id,
        "add",
        "lease",
        record.record_id,
        {"company_name": record.company_name, "new_project": record.new_project},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.patch("/{record_id}")
def update_lease(
    record_id: str,
    body: TenancyLeaseUpdate,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    force: bool = False,
):
    record = get_record_or_404(db, TenancyLease, record_id, device)
    ensure_can_edit(record, device)
    payload = body.model_dump(exclude_unset=True)
    merged = {column.name: getattr(record, column.name) for column in TenancyLease.__table__.columns}
    merged.update(payload)
    duplicates = find_duplicates(db, TenancyLease, merged, exclude_id=record_id)
    if duplicates and not force:
        raise duplicate_conflict(duplicates)
    changes = apply_payload(record, payload)
    log_operation(
        db,
        device.device_id,
        "update",
        "lease",
        record.record_id,
        {"changed_fields": sorted(changes.keys())},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.delete("/{record_id}")
def delete_lease(record_id: str, db: DbSession, device: CurrentDevice, request: Request):
    record = get_record_or_404(db, TenancyLease, record_id, device)
    ensure_can_edit(record, device)
    record.data_status = 0
    log_operation(
        db,
        device.device_id,
        "delete",
        "lease",
        record.record_id,
        {"company_name": record.company_name},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"record_id": record_id, "deleted": True, "recycle_days": 7}
