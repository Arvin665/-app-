from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from PIL import Image, ImageOps
from sqlalchemy import select

from app.api.deps import CurrentDevice, DbSession
from app.core.config import settings
from app.core.security import new_id
from app.models import Attachment
from app.services.record_utils import MODULE_MODELS, get_record_or_404, log_operation

router = APIRouter(prefix="/attachments", tags=["附件管理"])
MAX_FILE_SIZE = 50 * 1024 * 1024
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}


def classify_file(file_name: str, content_type: Optional[str]) -> str:
    """按扩展名与 MIME 归类，数据库只保存约定的 5 种类型。"""
    suffix = Path(file_name).suffix.lower()
    if suffix in IMAGE_SUFFIXES or (content_type or "").startswith("image/"):
        return "image"
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".xlsx", ".xls", ".csv"}:
        return "excel"
    if suffix in {".doc", ".docx"}:
        return "word"
    return "other"


def public_url(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    return f"{settings.public_base_url.rstrip('/')}/uploads/{normalized}"


def make_thumbnail(source: Path, target: Path) -> None:
    """图片统一纠正方向后生成 320px 缩略图，避免手机照片旋转异常。"""
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((320, 320))
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGB")
        image.save(target, format="JPEG", quality=82, optimize=True)


@router.post("", status_code=201)
async def upload_attachment(
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    biz_type: str = Form(...),
    biz_id: str = Form(...),
    file: UploadFile = File(...),
):
    if biz_type not in MODULE_MODELS:
        raise HTTPException(status_code=422, detail="biz_type 不正确")
    # 上传前先验证业务记录可读，防止通过附件接口探测他人私有记录。
    get_record_or_404(db, MODULE_MODELS[biz_type], biz_id, device)
    if not file.filename:
        raise HTTPException(status_code=422, detail="文件名不能为空")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="单个附件不能超过 50MB")
    if not content:
        raise HTTPException(status_code=422, detail="文件内容为空")

    attach_id = new_id()
    suffix = Path(file.filename).suffix.lower()[:20]
    relative_dir = Path(biz_type) / biz_id
    target_dir = Path(settings.upload_dir) / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{attach_id}{suffix}"
    target_path.write_bytes(content)

    file_type = classify_file(file.filename, file.content_type)
    thumbnail_path: Optional[Path] = None
    if file_type == "image":
        thumbnail_path = target_dir / f"{attach_id}.thumb.jpg"
        try:
            make_thumbnail(target_path, thumbnail_path)
        except (OSError, ValueError):
            # 损坏或不受支持的图片仍保留原件，不阻断录入。
            thumbnail_path = None

    relative_file = target_path.relative_to(Path(settings.upload_dir)).as_posix()
    relative_thumb = (
        thumbnail_path.relative_to(Path(settings.upload_dir)).as_posix() if thumbnail_path else None
    )
    record = Attachment(
        attach_id=attach_id,
        biz_id=biz_id,
        biz_type=biz_type,
        file_name=file.filename[:255],
        file_type=file_type,
        file_size=len(content),
        file_url=public_url(relative_file),
        thumbnail_url=public_url(relative_thumb) if relative_thumb else None,
        uploader_id=device.device_id,
        data_status=1,
    )
    db.add(record)
    log_operation(
        db,
        device.device_id,
        "add",
        biz_type,
        biz_id,
        {"attachment_id": attach_id, "file_name": record.file_name},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return {
        "attach_id": record.attach_id,
        "biz_id": record.biz_id,
        "biz_type": record.biz_type,
        "file_name": record.file_name,
        "file_type": record.file_type,
        "file_size": record.file_size,
        "file_url": record.file_url,
        "thumbnail_url": record.thumbnail_url,
        "preview_url": record.thumbnail_url or record.file_url,
        "upload_time": record.upload_time,
    }


@router.get("")
def list_attachments(
    db: DbSession,
    device: CurrentDevice,
    biz_type: str = Query(..., pattern=r"^(sale|lease|work|inspiration)$"),
    biz_id: str = Query(...),
):
    get_record_or_404(db, MODULE_MODELS[biz_type], biz_id, device)
    records = db.scalars(
        select(Attachment).where(
            Attachment.biz_type == biz_type,
            Attachment.biz_id == biz_id,
            Attachment.data_status == 1,
        )
    ).all()
    return {
        "items": [
            {
                "attach_id": item.attach_id,
                "file_name": item.file_name,
                "file_type": item.file_type,
                "file_size": item.file_size,
                "file_url": item.file_url,
                "thumbnail_url": item.thumbnail_url,
                "preview_url": item.thumbnail_url or item.file_url,
                "upload_time": item.upload_time,
            }
            for item in records
        ]
    }


@router.delete("/{attach_id}")
def delete_attachment(attach_id: str, db: DbSession, device: CurrentDevice, request: Request):
    record = db.get(Attachment, attach_id)
    if record is None or record.data_status != 1:
        raise HTTPException(status_code=404, detail="附件不存在")
    if record.uploader_id != device.device_id and device.role_level != 1:
        raise HTTPException(status_code=403, detail="只能删除本人上传的附件")
    # 再次校验关联业务记录权限，避免管理员借附件越权读取个人灵感角。
    get_record_or_404(db, MODULE_MODELS[record.biz_type], record.biz_id, device)
    record.data_status = 0
    log_operation(
        db,
        device.device_id,
        "delete",
        record.biz_type,
        record.biz_id,
        {"attachment_id": attach_id},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"attach_id": attach_id, "deleted": True}
