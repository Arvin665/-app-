from __future__ import annotations

import hmac
import hashlib
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

from fastapi import HTTPException

from app.core.config import settings


FILE_KINDS = {"material", "attachment"}
FILE_VARIANTS = {"original", "thumbnail"}


def _signature(kind: str, record_id: str, variant: str, expires: int) -> str:
    message = f"{kind}:{record_id}:{variant}:{expires}".encode("utf-8")
    return hmac.new(
        settings.sensitive_field_key.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()


def signed_file_url(
    kind: str,
    record_id: str,
    variant: str = "original",
    ttl_seconds: Optional[int] = None,
) -> str:
    """生成短期签名地址；数据库仍保存不可直接访问的规范原件地址。"""
    if kind not in FILE_KINDS or variant not in FILE_VARIANTS:
        raise ValueError("不支持的文件类型或版本")
    ttl = settings.file_url_ttl_seconds if ttl_seconds is None else int(ttl_seconds)
    expires = int(time.time()) + max(60, min(ttl, 7 * 24 * 3600))
    signature = _signature(kind, record_id, variant, expires)
    query = urlencode({"variant": variant, "expires": expires, "signature": signature})
    base = settings.public_base_url.rstrip("/")
    return f"{base}{settings.api_prefix}/files/{kind}/{record_id}?{query}"


def verify_file_signature(
    kind: str,
    record_id: str,
    variant: str,
    expires: int,
    signature: str,
) -> None:
    if kind not in FILE_KINDS or variant not in FILE_VARIANTS:
        raise HTTPException(status_code=404, detail="文件地址无效")
    if expires < int(time.time()):
        raise HTTPException(status_code=403, detail="文件地址已过期，请重新打开资料")
    expected = _signature(kind, record_id, variant, expires)
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="文件签名无效")


def upload_path_from_url(file_url: Optional[str]) -> Optional[Path]:
    """把历史或新写入的 /uploads/... 地址安全映射到上传目录。"""
    if not file_url:
        return None
    marker = "/uploads/"
    if marker not in file_url:
        return None
    relative = file_url.split(marker, 1)[1].lstrip("/")
    root = Path(settings.upload_dir).resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        return None
    return candidate if candidate.is_file() else None
