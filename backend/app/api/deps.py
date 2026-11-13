from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import normalize_device_id
from app.db.session import get_db
from app.models import Device
from app.services.cache import auth_cache


DbSession = Annotated[Session, Depends(get_db)]


# 所有受保护接口统一使用 X-Device-ID，不引入账号密码或长期 Token。
def get_current_device(
    db: DbSession,
    x_device_id: Annotated[str | None, Header(alias="X-Device-ID")] = None,
) -> Device:
    if not x_device_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少设备标识")
    try:
        device_id = normalize_device_id(x_device_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    device = db.scalar(select(Device).where(Device.device_id == device_id))
    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="设备未绑定邀请码")
    if device.status != 1:
        # 禁用设备即时失效，并清除 Redis 中可能残留的缓存。
        auth_cache.delete_device(device_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="设备已被管理员禁用")

    auth_cache.set_device(device_id, device.role_level)
    return device


CurrentDevice = Annotated[Device, Depends(get_current_device)]


def require_admin(device: CurrentDevice) -> Device:
    if device.role_level != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可执行此操作")
    return device


AdminDevice = Annotated[Device, Depends(require_admin)]
