from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentDevice, DbSession
from app.core.security import new_id
from app.models import PropertySale
from app.schemas.sale import PropertySaleCreate, PropertySaleUpdate
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

router = APIRouter(prefix="/sales", tags=["项目买卖信息"])


def duplicate_conflict(duplicates: list[PropertySale]) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "DUPLICATE_RECORD", "message": "发现相近买卖记录", "duplicates": duplicate_detail(duplicates)},
    )


def complete_sale_payload(payload: dict, create: bool = False) -> dict:
    """数据库仍保留必要列，片段资讯用明确占位值落库，不强迫用户先补全。"""
    normalized = dict(payload)
    if create or "project_name" in normalized:
        normalized["project_name"] = (str(normalized.get("project_name") or "").strip() or "待补充项目")[:100]
    if create or "district" in normalized:
        normalized["district"] = (str(normalized.get("district") or "").strip() or "待确认区域")[:50]
    if create or "deal_date" in normalized:
        normalized["deal_date"] = normalized.get("deal_date") or date.today()
    if create or "deal_status" in normalized:
        normalized["deal_status"] = (str(normalized.get("deal_status") or "").strip() or "信息待补充")[:20]
    return normalized


@router.get("")
def list_sales(
    db: DbSession,
    device: CurrentDevice,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    keyword: Optional[str] = None,
    project_name: Optional[str] = None,
    district: Optional[str] = None,
    deal_status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period_type: Optional[str] = Query(default=None, pattern=r"^(day|week|month|quarter|year)$"),
    period_value: Optional[str] = None,
):
    """团队共享买卖库，支持名称、区域、状态、日期和快速周期筛选。"""
    query = apply_soft_delete_scope(select(PropertySale), PropertySale)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(
            or_(
                PropertySale.project_name.like(pattern),
                PropertySale.address.like(pattern),
                PropertySale.buyer.like(pattern),
                PropertySale.seller.like(pattern),
                PropertySale.remark.like(pattern),
            )
        )
    if project_name:
        query = query.where(PropertySale.project_name.like(f"%{project_name.strip()}%"))
    if district:
        query = query.where(PropertySale.district.like(f"%{district.strip()}%"))
    if deal_status:
        query = query.where(PropertySale.deal_status == deal_status)
    if start_date:
        query = query.where(PropertySale.deal_date >= start_date)
    if end_date:
        query = query.where(PropertySale.deal_date <= end_date)
    query = apply_period_filter(query, PropertySale.deal_date, period_type, period_value)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.scalars(
        query.order_by(PropertySale.deal_date.desc(), PropertySale.update_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [serialize_record(record, device) for record in records],
        "total": total,
        "page": page,
        "page_size": page_size,
        "module": "sale",
        "can_view_sensitive": device.role_level == 1,
    }


@router.get("/{record_id}")
def get_sale(record_id: str, db: DbSession, device: CurrentDevice):
    return serialize_record(get_record_or_404(db, PropertySale, record_id, device), device)


@router.post("", status_code=201)
def create_sale(
    body: PropertySaleCreate,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    force: bool = False,
):
    """重复录入返回 409 与候选记录；前端确认后才可带 force=true 写入。"""
    payload = complete_sale_payload(body.model_dump(), create=True)
    duplicates = find_duplicates(db, PropertySale, payload)
    if duplicates and not force:
        raise duplicate_conflict(duplicates)

    record = PropertySale(record_id=new_id(), creator_id=device.device_id, data_status=1)
    apply_payload(record, payload)
    db.add(record)
    log_operation(
        db,
        device.device_id,
        "add",
        "sale",
        record.record_id,
        {"project_name": record.project_name, "deal_date": str(record.deal_date)},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.patch("/{record_id}")
def update_sale(
    record_id: str,
    body: PropertySaleUpdate,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    force: bool = False,
):
    """局部更新；并发写入采用服务端最后更新时间覆盖规则。"""
    record = get_record_or_404(db, PropertySale, record_id, device)
    ensure_can_edit(record, device)
    payload = complete_sale_payload(body.model_dump(exclude_unset=True))
    merged = {column.name: getattr(record, column.name) for column in PropertySale.__table__.columns}
    merged.update(payload)
    duplicates = find_duplicates(db, PropertySale, merged, exclude_id=record_id)
    if duplicates and not force:
        raise duplicate_conflict(duplicates)
    changes = apply_payload(record, payload)
    log_operation(
        db,
        device.device_id,
        "update",
        "sale",
        record.record_id,
        {"changed_fields": sorted(changes.keys()), "values": changes},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.delete("/{record_id}")
def delete_sale(record_id: str, db: DbSession, device: CurrentDevice, request: Request):
    """软删除进入 7 天回收站，不执行物理 DELETE。"""
    record = get_record_or_404(db, PropertySale, record_id, device)
    ensure_can_edit(record, device)
    record.data_status = 0
    log_operation(
        db,
        device.device_id,
        "delete",
        "sale",
        record.record_id,
        {"project_name": record.project_name},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"record_id": record_id, "deleted": True, "recycle_days": 7}
