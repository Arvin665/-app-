import json
import secrets
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select

from app.api.deps import AdminDevice, CurrentDevice, DbSession
from app.core.config import settings
from app.models import (
    Attachment,
    Device,
    InviteCode,
    Material,
    OperationLog,
    PersonalInspiration,
    PropertySale,
    TenancyLease,
    WorkLog,
)
from app.services.record_utils import business_date_of, log_operation, permissions_for, role_name, serialize_record
from app.services.backup_utils import model_to_dict

router = APIRouter(prefix="/admin", tags=["管理员"])


class DeviceStatusRequest(BaseModel):
    status: int = Field(ge=0, le=1)


def serialize_invite(invite: InviteCode) -> dict:
    return {
        "id": invite.id,
        "invite_code": invite.invite_code,
        "valid_start": invite.valid_start,
        "valid_end": invite.valid_end,
        "max_use_count": invite.max_use_count,
        "used_count": invite.used_count,
        "remaining_count": max(invite.max_use_count - invite.used_count, 0),
        "role_level": invite.role_level,
        "status": invite.status,
        "creator_id": invite.creator_id,
        "create_time": invite.create_time,
    }


@router.post("/invites", status_code=201)
def create_invite(body: dict, db: DbSession, device: AdminDevice, request: Request):
    """生成 6 位数字邀请码；有效期与使用次数完全由管理员控制。"""
    valid_start = body.get("valid_start")
    valid_end = body.get("valid_end")
    start = datetime.fromisoformat(valid_start) if valid_start else datetime.now()
    end = datetime.fromisoformat(valid_end) if valid_end else start + timedelta(days=7)
    max_use_count = int(body.get("max_use_count", 10))
    role_level = int(body.get("role_level", 2))
    if end <= start:
        raise HTTPException(status_code=422, detail="失效时间必须晚于生效时间")
    if max_use_count < 1 or max_use_count > 10000:
        raise HTTPException(status_code=422, detail="使用次数必须在 1-10000 之间")
    if role_level not in {1, 2}:
        raise HTTPException(status_code=422, detail="权限等级只能是 1 或 2")

    for _ in range(20):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not db.scalar(select(InviteCode.id).where(InviteCode.invite_code == code)):
            break
    else:
        raise HTTPException(status_code=500, detail="邀请码生成失败，请重试")
    invite = InviteCode(
        invite_code=code,
        valid_start=start,
        valid_end=end,
        max_use_count=max_use_count,
        used_count=0,
        role_level=role_level,
        status=1,
        creator_id=device.device_id,
    )
    db.add(invite)
    log_operation(
        db,
        device.device_id,
        "add",
        "work",
        None,
        {"operation": "create_invite", "invite_code": code, "role_level": role_level},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(invite)
    return serialize_invite(invite)


@router.get("/invites")
def list_invites(
    db: DbSession,
    device: AdminDevice,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    status: Optional[int] = Query(default=None, ge=0, le=1),
):
    query = select(InviteCode)
    if status is not None:
        query = query.where(InviteCode.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    invites = db.scalars(query.order_by(InviteCode.create_time.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [serialize_invite(item) for item in invites], "total": total, "page": page, "page_size": page_size}


@router.patch("/invites/{invite_id}/status")
def set_invite_status(
    invite_id: int,
    body: DeviceStatusRequest,
    db: DbSession,
    device: AdminDevice,
    request: Request,
):
    invite = db.get(InviteCode, invite_id)
    if invite is None:
        raise HTTPException(status_code=404, detail="邀请码不存在")
    invite.status = body.status
    log_operation(
        db,
        device.device_id,
        "update",
        "work",
        None,
        {"operation": "invite_status", "invite_id": invite_id, "status": body.status},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(invite)
    return serialize_invite(invite)


@router.get("/devices")
def list_devices(
    db: DbSession,
    device: AdminDevice,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    keyword: Optional[str] = None,
    status: Optional[int] = Query(default=None, ge=0, le=1),
):
    query = select(Device)
    if keyword:
        query = query.where(Device.device_name.like(f"%{keyword.strip()}%") | Device.device_id.like(f"%{keyword.strip()}%"))
    if status is not None:
        query = query.where(Device.status == status)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    devices = db.scalars(query.order_by(Device.bind_time.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "device_id": item.device_id,
                "device_name": item.device_name,
                "invite_code": item.invite_code,
                "role_level": item.role_level,
                "role_name": role_name(item.role_level),
                "permissions": permissions_for(item.role_level),
                "bind_time": item.bind_time,
                "last_online_time": item.last_online_time,
                "status": item.status,
            }
            for item in devices
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/devices/{device_id}/status")
def set_device_status(
    device_id: str,
    body: DeviceStatusRequest,
    db: DbSession,
    device: AdminDevice,
    request: Request,
):
    if device_id == device.device_id and body.status == 0:
        raise HTTPException(status_code=400, detail="不能禁用当前管理员设备")
    target = db.get(Device, device_id)
    if target is None:
        raise HTTPException(status_code=404, detail="设备不存在")
    target.status = body.status
    log_operation(
        db,
        device.device_id,
        "update",
        "work",
        None,
        {"operation": "device_status", "target_device": device_id, "status": body.status},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"device_id": device_id, "status": body.status}


@router.get("/logs")
def list_logs(
    db: DbSession,
    device: AdminDevice,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=1000),
    biz_module: Optional[str] = Query(default=None, pattern=r"^(sale|lease|work|inspiration)$"),
    operation_type: Optional[str] = Query(default=None, pattern=r"^(add|update|delete|export)$"),
    target_device: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
):
    query = select(OperationLog)
    if biz_module:
        query = query.where(OperationLog.biz_module == biz_module)
    if operation_type:
        query = query.where(OperationLog.operation_type == operation_type)
    if target_device:
        query = query.where(OperationLog.device_id == target_device)
    if start_time:
        query = query.where(OperationLog.create_time >= start_time)
    if end_time:
        query = query.where(OperationLog.create_time <= end_time)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    logs = db.scalars(query.order_by(OperationLog.create_time.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return {
        "items": [
            {
                "log_id": item.log_id,
                "device_id": item.device_id,
                "operation_type": item.operation_type,
                "biz_module": item.biz_module,
                "biz_record_id": item.biz_record_id,
                "operation_content": item.operation_content,
                "ip_address": item.ip_address,
                "create_time": item.create_time,
            }
            for item in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/statistics")
def statistics(db: DbSession, device: AdminDevice):
    """管理台概览只统计团队共享口径与设备状态，不读取他人个人记录。"""
    sale_count = db.scalar(select(func.count()).where(PropertySale.data_status == 1)) or 0
    lease_count = db.scalar(select(func.count()).where(TenancyLease.data_status == 1)) or 0
    shared_work_count = db.scalar(
        select(func.count()).where(WorkLog.data_status == 1, WorkLog.is_shared == 1)
    ) or 0
    device_count = db.scalar(select(func.count()).where(Device.status == 1)) or 0
    return {
        "sale_count": sale_count,
        "lease_count": lease_count,
        "shared_work_count": shared_work_count,
        "active_device_count": device_count,
        "notice": "个人灵感及私有工作记录不进入管理员统计明细。",
    }


# 备份恢复只合并业务表、附件和资料资产，不覆盖设备身份，避免意外锁死管理员。
BACKUP_MODELS = {
    "biz_property_sale": PropertySale,
    "biz_tenancy_lease": TenancyLease,
    "biz_work_log": WorkLog,
    "biz_personal_inspiration": PersonalInspiration,
    "sys_attachment": Attachment,
    "sys_material": Material,
}


def backup_rows_for(db: DbSession, model, device: Device) -> list:
    """返回管理员当前可读取的数据，避免备份接口绕开个人隐私隔离。"""
    if model is PersonalInspiration:
        return list(
            db.scalars(
                select(PersonalInspiration).where(PersonalInspiration.creator_id == device.device_id)
            ).all()
        )
    if model is WorkLog:
        return list(
            db.scalars(
                select(WorkLog).where(
                    (WorkLog.creator_id == device.device_id) | (WorkLog.is_shared == 1)
                )
            ).all()
        )
    if model is Attachment:
        visible_ids: dict[str, set[str]] = {
            "sale": set(db.scalars(select(PropertySale.record_id)).all()),
            "lease": set(db.scalars(select(TenancyLease.record_id)).all()),
            "work": {row.record_id for row in backup_rows_for(db, WorkLog, device)},
            "inspiration": {
                row.record_id for row in backup_rows_for(db, PersonalInspiration, device)
            },
        }
        rows = db.scalars(select(Attachment).order_by(Attachment.upload_time.desc())).all()
        return [
            row
            for row in rows
            if row.data_status == 1 and row.biz_id in visible_ids.get(row.biz_type, set())
        ]
    if model is Material:
        shared_work_ids = select(WorkLog.record_id).where(
            WorkLog.data_status == 1,
            WorkLog.is_shared == 1,
        )
        return list(
            db.scalars(
                select(Material)
                .where(
                    Material.data_status == 1,
                    or_(
                        Material.module.in_(["sale", "lease"]),
                        Material.uploader_id == device.device_id,
                        and_(Material.module == "work", Material.record_id.in_(shared_work_ids)),
                    ),
                )
                .order_by(Material.upload_time.desc())
            ).all()
        )
    return list(db.scalars(select(model)).all())


def coerce_value(column, value):
    if value is None:
        return None
    python_type = column.type.python_type
    if python_type is datetime:
        return datetime.fromisoformat(str(value))
    if python_type is date:
        return date.fromisoformat(str(value)[:10])
    if python_type is Decimal:
        return Decimal(str(value))
    if python_type in {int, float, str, bool}:
        return python_type(value)
    return value


@router.get("/backup")
def download_full_backup(db: DbSession, device: AdminDevice, request: Request):
    """生成含业务数据、账号元数据与附件原件的 ZIP，供异地备份留存。"""
    tables = {}
    for table_name, model in BACKUP_MODELS.items():
        rows = backup_rows_for(db, model, device)
        tables[table_name] = [model_to_dict(row, decrypt_sensitive=model is PropertySale) for row in rows]
    tables["sys_device"] = [
        {
            "device_id": item.device_id,
            "device_name": item.device_name,
            "invite_code": item.invite_code,
            "role_level": item.role_level,
            "bind_time": item.bind_time,
            "last_online_time": item.last_online_time,
            "status": item.status,
        }
        for item in db.scalars(select(Device)).all()
    ]
    tables["sys_invite_code"] = [serialize_invite(item) for item in db.scalars(select(InviteCode)).all()]
    payload = {
        "version": 2,
        "exported_at": datetime.now().isoformat(),
        "database": "mall_office_asset",
        "tables": tables,
    }
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("database.json", json.dumps(payload, ensure_ascii=False, default=str, indent=2))
        uploads_root = Path(settings.upload_dir)
        prefix = f"{settings.public_base_url.rstrip('/')}/uploads/"
        for model in (Attachment, Material):
            for record in backup_rows_for(db, model, device):
                for field in ("file_url", "thumbnail_url"):
                    url = getattr(record, field, None)
                    if not url or not url.startswith(prefix):
                        continue
                    relative = url[len(prefix) :]
                    source = uploads_root / relative
                    if source.is_file():
                        archive.write(source, f"uploads/{relative}")
    log_operation(db, device.device_id, "export", "sale", None, {"operation": "full_backup"}, request.client.host if request.client else None)
    db.commit()
    buffer.seek(0)
    filename = f"asset_backup_{datetime.now():%Y%m%d_%H%M%S}.zip"
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/backup/restore")
async def restore_backup(
    db: DbSession,
    device: AdminDevice,
    request: Request,
    file: UploadFile = File(...),
):
    """按主键合并恢复备份；已有记录覆盖，缺失记录新增，不做全库清空。"""
    content = await file.read()
    if len(content) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="备份包不能超过 200MB")
    try:
        with zipfile.ZipFile(BytesIO(content)) as archive:
            payload = json.loads(archive.read("database.json").decode("utf-8"))
            tables = payload.get("tables", {})
            restored = 0
            uploads_root = Path(settings.upload_dir).resolve()
            for member in archive.infolist():
                if not member.filename.startswith("uploads/") or member.is_dir():
                    continue
                target = (uploads_root / member.filename.removeprefix("uploads/")).resolve()
                if uploads_root not in target.parents:
                    raise HTTPException(status_code=400, detail="备份包包含非法文件路径")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member))
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="备份包格式不正确") from exc

    for table_name, model in BACKUP_MODELS.items():
        for row in tables.get(table_name, []):
            row = {key: value for key, value in row.items() if key in model.__table__.columns}
            primary_key = list(model.__table__.primary_key.columns)[0].name
            record_id = row.get(primary_key)
            if not record_id:
                continue
            record = db.get(model, record_id)
            plaintext_commission = row.pop("commission_remark", None) if model is PropertySale else None
            values = {key: coerce_value(model.__table__.columns[key], value) for key, value in row.items()}
            if record is None:
                record = model()
            for key, value in values.items():
                setattr(record, key, value)
            if model is PropertySale:
                record.set_commission_remark(plaintext_commission)
            db.add(record)
            restored += 1
    log_operation(
        db,
        device.device_id,
        "update",
        "sale",
        None,
        {"operation": "restore_backup", "rows": restored},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"restored_rows": restored, "mode": "merge", "notice": "已按主键合并，未清空现有数据。"}
