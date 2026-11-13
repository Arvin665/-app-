import base64
import hashlib
import re
import uuid
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

DEVICE_ID_PATTERN = re.compile(r"^[a-fA-F0-9]{32}$")
INVITE_CODE_PATTERN = re.compile(r"^\d{6}$")


def normalize_device_id(raw_device_id: str) -> str:
    """设备标识统一为 32 位十六进制，防止大小写差异造成重复用户。"""
    device_id = (raw_device_id or "").strip().lower()
    if not DEVICE_ID_PATTERN.fullmatch(device_id):
        raise ValueError("device_id 必须是 32 位十六进制字符串")
    return device_id


def is_valid_invite_code(code: str) -> bool:
    return bool(INVITE_CODE_PATTERN.fullmatch((code or "").strip()))


def new_id() -> str:
    """数据库主键统一使用 32 位 UUID，与设备 ID 长度保持一致。"""
    return uuid.uuid4().hex


def _fernet() -> Fernet:
    """使用部署密钥派生固定 Fernet 密钥，避免把数据库密钥写进代码。"""
    digest = hashlib.sha256(settings.sensitive_field_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_sensitive(value: Optional[str]) -> Optional[str]:
    """空值保持为空；非空敏感内容统一加上 enc:v1 前缀。"""
    if value is None or value == "":
        return value
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"enc:v1:{token}"


def decrypt_sensitive(value: Optional[str]) -> Optional[str]:
    """兼容早期明文数据；无法解密时不把密文误当成可读明文返回。"""
    if value is None or value == "":
        return value
    if not value.startswith("enc:v1:"):
        return value
    try:
        return _fernet().decrypt(value.removeprefix("enc:v1:").encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return "[敏感字段无法解密，请检查 SENSITIVE_FIELD_KEY]"
