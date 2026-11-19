from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.api.deps import DbSession
from app.models import Attachment, Material
from app.services.file_access import (
    upload_path_from_url,
    verify_file_signature,
)

router = APIRouter(prefix="/files", tags=["签名文件下载"])


def resolve_file(
    kind: Literal["material", "attachment"],
    record_id: str,
    variant: Literal["original", "thumbnail"],
    db: DbSession,
) -> tuple[Path, str, str | None]:
    if kind == "material":
        record = db.scalar(
            select(Material).where(
                Material.material_id == record_id,
                Material.data_status == 1,
            )
        )
        if record is None:
            raise HTTPException(status_code=404, detail="资料不存在")
        path = upload_path_from_url(record.thumbnail_url if variant == "thumbnail" else record.file_url)
        if path is None and variant == "thumbnail":
            path = upload_path_from_url(record.file_url)
        if path is None:
            raise HTTPException(status_code=404, detail="资料原件不存在")
        return path, record.file_name, record.mime_type
    record = db.scalar(
        select(Attachment).where(
            Attachment.attach_id == record_id,
            Attachment.data_status == 1,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="附件不存在")
    path = upload_path_from_url(record.thumbnail_url if variant == "thumbnail" else record.file_url)
    if path is None and variant == "thumbnail":
        path = upload_path_from_url(record.file_url)
    if path is None:
        raise HTTPException(status_code=404, detail="附件原件不存在")
    return path, record.file_name, None


@router.get("/{kind}/{record_id}")
def download_file(
    kind: Literal["material", "attachment"],
    record_id: str,
    db: DbSession,
    variant: Literal["original", "thumbnail"] = Query(default="original"),
    expires: int = Query(...),
    signature: str = Query(..., min_length=64, max_length=64),
):
    """签名 URL 是可短期分享的只读访问凭证，不暴露上传目录。"""
    verify_file_signature(kind, record_id, variant, expires, signature)
    path, filename, media_type = resolve_file(kind, record_id, variant, db)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="文件原件不存在")
    return FileResponse(
        path,
        media_type=media_type,
        filename=filename,
        content_disposition_type="inline",
    )
