import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Optional, Type

from fastapi import HTTPException, status
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from app.core.security import new_id
from app.models import Device, InviteCode, OperationLog, PersonalInspiration, PropertySale, TenancyLease, WorkLog
from app.models.common import BusinessRecordMixin

MODULE_MODELS = {
    "sale": PropertySale,
    "lease": TenancyLease,
    "work": WorkLog,
    "inspiration": PersonalInspiration,
}
MODULE_NAMES = {
    "sale": "项目买卖信息",
    "lease": "企业租赁信息",
    "work": "工作记录",
    "inspiration": "个人灵感角",
}
BUSINESS_DATE_FIELDS = {
    PropertySale: "deal_date",
    TenancyLease: "start_date",
    WorkLog: "record_date",
    PersonalInspiration: "record_time",
}
RECYCLE_DAYS = 7
SALE_DUPLICATE_DAYS = 7

ROLE_PERMISSIONS = {
    1: [
        "read:shared",
        "write:own",
        "edit:shared",
        "admin:invite",
        "admin:device",
        "admin:export",
        "admin:backup",
        "recycle:all",
    ],
    2: ["read:shared", "write:own", "recycle:own"],
}


def role_name(role_level: int) -> str:
    return "管理员" if role_level == 1 else "普通成员"


def permissions_for(role_level: int) -> list[str]:
    return ROLE_PERMISSIONS.get(role_level, ROLE_PERMISSIONS[2])


def business_date_of(record: Any) -> Optional[date]:
    """统一取业务日期；租赁未填起租日时退回创建日期避免排序崩溃。"""
    if isinstance(record, PropertySale):
        return record.deal_date
    if isinstance(record, TenancyLease):
        return record.start_date or record.create_time.date()
    if isinstance(record, WorkLog):
        return record.record_date
    if isinstance(record, PersonalInspiration):
        return record.record_time.date()
    return None


def archive_of(record: Any) -> dict[str, Any]:
    """业务日期自动派生日、周、月、季、年归档口径。"""
    business_date = business_date_of(record)
    if business_date is None:
        return {}
    iso = business_date.isocalendar()
    return {
        "business_date": business_date.isoformat(),
        "day": business_date.isoformat(),
        "week": f"{iso.year}-W{iso.week:02d}",
        "month": business_date.strftime("%Y-%m"),
        "quarter": f"{business_date.year}-Q{(business_date.month - 1) // 3 + 1}",
        "year": str(business_date.year),
    }


def can_read(record: Any, device: Device) -> bool:
    """读权限是本系统防越权的最后一道保险，不依赖前端隐藏。"""
    if record.data_status != 1:
        return False
    if isinstance(record, PersonalInspiration):
        return record.creator_id == device.device_id
    if isinstance(record, WorkLog):
        return record.creator_id == device.device_id or record.is_shared == 1
    return True


def can_edit(record: Any, device: Device, include_deleted: bool = False) -> bool:
    """管理员可编辑团队共享内容；灵感角永远只能由创建人操作。"""
    if isinstance(record, PersonalInspiration):
        return record.creator_id == device.device_id and (include_deleted or record.data_status == 1)
    if isinstance(record, WorkLog):
        if record.creator_id == device.device_id:
            return include_deleted or record.data_status == 1
        return device.role_level == 1 and record.is_shared == 1 and (include_deleted or record.data_status == 1)
    return (device.role_level == 1 or record.creator_id == device.device_id) and (
        include_deleted or record.data_status == 1
    )


def scope_condition(model: Type[BusinessRecordMixin], device: Device):
    """把团队共享与个人隔离规则转成 SQL 条件。"""
    if model is PersonalInspiration:
        return model.creator_id == device.device_id
    if model is WorkLog:
        return or_(model.creator_id == device.device_id, model.is_shared == 1)
    return True


def apply_soft_delete_scope(query: Select, model: Type[BusinessRecordMixin], deleted_only: bool = False) -> Select:
    if deleted_only:
        cutoff = datetime.now() - timedelta(days=RECYCLE_DAYS)
        return query.where(model.data_status == 0, model.update_time >= cutoff)
    return query.where(model.data_status == 1)


def serialize_record(record: Any, device: Device) -> dict[str, Any]:
    """按数据库列输出，敏感佣金仅管理员可见；归档字段为派生只读数据。"""
    payload: dict[str, Any] = {}
    for column in record.__table__.columns:
        value = getattr(record, column.name)
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        payload[column.name] = value
    if isinstance(record, PropertySale):
        # 普通成员永远看不到密文或明文，只有管理员序列化时解密。
        payload["commission_remark"] = record.decrypted_commission_remark if device.role_level == 1 else None
    payload["archive"] = archive_of(record)
    payload["can_edit"] = can_edit(record, device)
    return payload


def get_record_or_404(
    db: Session,
    model: Type[BusinessRecordMixin],
    record_id: str,
    device: Device,
    include_deleted: bool = False,
) -> Any:
    record = db.get(model, record_id)
    if record is None or (not include_deleted and record.data_status != 1):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    if include_deleted:
        if not can_edit(record, device, include_deleted=True):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该记录")
    elif not can_read(record, device):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该记录")
    return record


def ensure_can_edit(record: Any, device: Device) -> None:
    if not can_edit(record, device):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能修改本人创建的内容")


def log_operation(
    db: Session,
    device_id: str,
    operation_type: str,
    biz_module: str,
    biz_record_id: Optional[str] = None,
    content: Optional[dict[str, Any] | list[Any] | str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """审计日志与业务写入处于同一事务，业务失败时一起回滚。"""
    encoded = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False, default=str)
    db.add(
        OperationLog(
            log_id=new_id(),
            device_id=device_id,
            operation_type=operation_type,
            biz_module=biz_module,
            biz_record_id=biz_record_id,
            operation_content=encoded,
            ip_address=ip_address,
        )
    )


def apply_payload(record: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """过滤主键和审计字段，防止客户端伪造创建人；佣金走专用加密方法。"""
    immutable = {"record_id", "creator_id", "create_time", "update_time", "data_status"}
    changes: dict[str, Any] = {}
    for key, value in payload.items():
        if key in immutable:
            continue
        if key == "commission_remark" and isinstance(record, PropertySale):
            setattr(record, "commission_remark", None)
            record.set_commission_remark(value)
            changes[key] = "[已加密更新]" if value else None
            continue
        setattr(record, key, value)
        changes[key] = value
    return changes


def find_duplicates(
    db: Session,
    model: Type[BusinessRecordMixin],
    payload: dict[str, Any],
    exclude_id: Optional[str] = None,
) -> list[Any]:
    """买卖按项目名+7天内交易；租赁按企业名+新办公项目。"""
    if model is PropertySale:
        deal_date = payload.get("deal_date")
        project_name = payload.get("project_name")
        if not deal_date or not project_name:
            return []
        if isinstance(deal_date, str):
            deal_date = date.fromisoformat(deal_date)
        conditions = [
            PropertySale.data_status == 1,
            PropertySale.project_name == project_name,
            PropertySale.deal_date >= deal_date - timedelta(days=SALE_DUPLICATE_DAYS),
            PropertySale.deal_date <= deal_date + timedelta(days=SALE_DUPLICATE_DAYS),
        ]
        if exclude_id:
            conditions.append(PropertySale.record_id != exclude_id)
        return list(db.scalars(select(PropertySale).where(and_(*conditions))))
    if model is TenancyLease:
        company_name = payload.get("company_name")
        new_project = payload.get("new_project")
        if not company_name or not new_project:
            return []
        conditions = [
            TenancyLease.data_status == 1,
            TenancyLease.company_name == company_name,
            TenancyLease.new_project == new_project,
        ]
        if exclude_id:
            conditions.append(TenancyLease.record_id != exclude_id)
        return list(db.scalars(select(TenancyLease).where(and_(*conditions))))
    return []


def duplicate_detail(records: list[Any]) -> list[dict[str, Any]]:
    result = []
    for record in records:
        result.append(
            {
                "record_id": record.record_id,
                "business_date": business_date_of(record).isoformat() if business_date_of(record) else None,
                "summary": getattr(record, "project_name", None)
                or getattr(record, "company_name", None)
                or getattr(record, "content", "")[:60],
            }
        )
    return result


def invite_is_usable(invite: InviteCode, now: datetime) -> bool:
    return (
        invite.status == 1
        and invite.valid_start <= now <= invite.valid_end
        and invite.used_count < invite.max_use_count
    )
