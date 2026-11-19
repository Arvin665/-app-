from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from starlette.concurrency import run_in_threadpool

from app.api.attachments import MAX_FILE_SIZE, make_thumbnail, public_url
from app.api.deps import CurrentDevice, DbSession
from app.core.config import settings
from app.core.security import new_id
from app.models import Material, WorkLog
from app.services.file_access import signed_file_url
from app.services.material_extract import extract_material, json_dump
from app.services.record_utils import MODULE_MODELS, get_record_or_404, log_operation

router = APIRouter(prefix="/materials", tags=["资料资产库"])


class MaterialLinkRequest(BaseModel):
    record_id: str = Field(min_length=1, max_length=32)


def parse_json(value: Optional[str], fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def visible_condition(device: CurrentDevice):
    """买卖/租赁资料团队可见；工作与灵感默认只对上传者可见。"""
    shared_work_ids = select(WorkLog.record_id).where(
        WorkLog.data_status == 1,
        WorkLog.is_shared == 1,
    )
    return or_(
        Material.module.in_(["sale", "lease"]),
        Material.uploader_id == device.device_id,
        and_(Material.module == "work", Material.record_id.in_(shared_work_ids)),
    )


def material_or_404(material_id: str, db: DbSession, device: CurrentDevice) -> Material:
    record = db.scalar(
        select(Material).where(
            Material.material_id == material_id,
            Material.data_status == 1,
            visible_condition(device),
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="资料不存在或无权访问")
    return record


def serialize_material(record: Material, include_text: bool = False) -> dict[str, Any]:
    return serialize_material_for_device(record, include_text=include_text, device=None)


def serialize_material_for_device(
    record: Material, device: Any, include_text: bool = False
) -> dict[str, Any]:
    structured = parse_json(record.extracted_data, {"fields": {}, "confidence": {}})
    metadata = parse_json(record.metadata_json, {})
    text = record.extracted_text or ""
    file_url = signed_file_url("material", record.material_id, "original")
    thumbnail_url = (
        signed_file_url("material", record.material_id, "thumbnail")
        if record.thumbnail_url
        else None
    )
    payload = {
        "material_id": record.material_id,
        "module": record.module,
        "record_id": record.record_id,
        "title": record.title,
        "file_name": record.file_name,
        "file_type": record.file_type,
        "mime_type": record.mime_type,
        "file_size": record.file_size,
        "file_url": file_url,
        "thumbnail_url": thumbnail_url,
        "preview_url": thumbnail_url or file_url,
        "extraction_status": record.extraction_status,
        "extraction_note": record.extraction_note,
        "extracted_fields": structured.get("fields", {}),
        "confidence": structured.get("confidence", {}),
        "metadata": metadata,
        "has_extracted_text": bool(text.strip()),
        "extracted_text_preview": text[:360],
        "uploader_id": record.uploader_id,
        "upload_time": record.upload_time,
        "can_delete": True,
    }
    if device is not None:
        payload["can_delete"] = (
            record.uploader_id == device.device_id or getattr(device, "role_level", 2) == 1
        )
    if include_text:
        payload["extracted_text"] = text
    return payload


@router.post("/upload", status_code=201)
async def upload_material(
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    module: str = Form(...),
    file: UploadFile = File(...),
    record_id: Optional[str] = Form(default=None),
    title: Optional[str] = Form(default=None),
):
    if module not in MODULE_MODELS:
        raise HTTPException(status_code=422, detail="module 参数不正确")
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名不能为空")
    if record_id:
        get_record_or_404(db, MODULE_MODELS[module], record_id, device)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="单个文件不能超过 50MB")
    if not content:
        raise HTTPException(status_code=422, detail="文件内容为空")

    material_id = new_id()
    suffix = Path(file.filename).suffix.lower()[:20]
    relative_dir = Path("materials") / module / material_id
    target_dir = Path(settings.upload_dir) / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{material_id}{suffix}"
    target_path.write_bytes(content)
    # 先落盘再识别。识别服务超时或异常时，用户上传的原件仍然存在。
    extraction = await run_in_threadpool(
        extract_material, content, file.filename, file.content_type, module
    )

    thumbnail_path: Optional[Path] = None
    if extraction["file_type"] == "image":
        thumbnail_path = target_dir / f"{material_id}.thumb.jpg"
        try:
            make_thumbnail(target_path, thumbnail_path)
        except (OSError, ValueError):
            thumbnail_path = None

    relative_file = target_path.relative_to(Path(settings.upload_dir)).as_posix()
    relative_thumb = (
        thumbnail_path.relative_to(Path(settings.upload_dir)).as_posix() if thumbnail_path else None
    )
    record = Material(
        material_id=material_id,
        module=module,
        record_id=record_id or None,
        title=(title or extraction["title"] or file.filename)[:255],
        file_name=file.filename[:255],
        file_type=extraction["file_type"],
        mime_type=(file.content_type or "")[:100] or None,
        file_size=len(content),
        file_url=public_url(relative_file),
        thumbnail_url=public_url(relative_thumb) if relative_thumb else None,
        extraction_status=extraction["status"],
        extracted_text=extraction["text"] or None,
        extracted_data=json_dump(extraction["structured"]),
        metadata_json=json_dump(extraction["metadata"]),
        extraction_note=extraction["note"],
        uploader_id=device.device_id,
        data_status=1,
    )
    db.add(record)
    log_operation(
        db,
        device.device_id,
        "add",
        module,
        record_id,
        {"material_id": material_id, "file_name": record.file_name, "status": record.extraction_status},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    result = serialize_material_for_device(record, device, include_text=True)
    result["note"] = extraction["note"]
    return result


@router.get("")
def list_materials(
    db: DbSession,
    device: CurrentDevice,
    module: Optional[str] = Query(default=None, pattern=r"^(sale|lease|work|inspiration)$"),
    file_type: Optional[str] = None,
    keyword: Optional[str] = None,
    record_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=200),
):
    conditions = [Material.data_status == 1, visible_condition(device)]
    if module:
        conditions.append(Material.module == module)
    if file_type:
        conditions.append(Material.file_type == file_type)
    if record_id:
        conditions.append(Material.record_id == record_id)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        conditions.append(
            or_(
                Material.title.like(pattern),
                Material.file_name.like(pattern),
                Material.extracted_text.like(pattern),
            )
        )
    query = select(Material).where(*conditions)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.scalars(
        query.order_by(Material.upload_time.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [serialize_material_for_device(item, device) for item in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{material_id}")
def get_material(material_id: str, db: DbSession, device: CurrentDevice):
    return serialize_material_for_device(material_or_404(material_id, db, device), device, include_text=True)


@router.post("/{material_id}/link")
def link_material(material_id: str, body: MaterialLinkRequest, db: DbSession, device: CurrentDevice):
    record = material_or_404(material_id, db, device)
    if record.uploader_id != device.device_id and device.role_level != 1:
        raise HTTPException(status_code=403, detail="只能关联本人上传的资料")
    get_record_or_404(db, MODULE_MODELS[record.module], body.record_id, device)
    record.record_id = body.record_id
    db.commit()
    db.refresh(record)
    return serialize_material_for_device(record, device)


@router.delete("/{material_id}")
def delete_material(material_id: str, db: DbSession, device: CurrentDevice, request: Request):
    record = material_or_404(material_id, db, device)
    if record.uploader_id != device.device_id and device.role_level != 1:
        raise HTTPException(status_code=403, detail="只能删除本人上传的资料")
    record.data_status = 0
    log_operation(
        db,
        device.device_id,
        "delete",
        record.module,
        record.record_id,
        {"material_id": material_id, "file_name": record.file_name},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"material_id": material_id, "deleted": True}
