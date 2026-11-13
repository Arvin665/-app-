from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentDevice, DbSession
from app.core.config import settings
from app.core.security import normalize_device_id
from app.models import Device, InviteCode
from app.schemas.auth import BindRequest, DeviceResponse, HeartbeatResponse
from app.services.cache import auth_cache
from app.services.record_utils import invite_is_usable, permissions_for, role_name

router = APIRouter(prefix="/auth", tags=["设备认证"])


def device_response(device: Device) -> DeviceResponse:
    return DeviceResponse(
        device_id=device.device_id,
        device_name=device.device_name,
        invite_code=device.invite_code,
        role_level=device.role_level,
        role_name=role_name(device.role_level),
        bind_time=device.bind_time,
        last_online_time=device.last_online_time,
        status=device.status,
        permissions=permissions_for(device.role_level),
    )


@router.post("/bind", response_model=DeviceResponse)
def bind_device(body: BindRequest, db: DbSession):
    """首次输入邀请码绑定；同一设备重复调用直接返回现有身份。"""
    try:
        device_id = normalize_device_id(body.device_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    existing = db.get(Device, device_id)
    if existing:
        if existing.status != 1:
            raise HTTPException(status_code=403, detail="设备已被管理员禁用")
        existing.last_online_time = datetime.now()
        db.commit()
        return device_response(existing)

    now = datetime.now()
    # FOR UPDATE 防止同一邀请码被并发超额使用；SQLite 测试库会安全忽略该锁。
    invite = db.scalar(
        select(InviteCode).where(InviteCode.invite_code == body.invite_code).with_for_update()
    )
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="邀请码不存在")
    if not invite_is_usable(invite, now):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邀请码已过期、停用或使用次数已达上限")

    device = Device(
        device_id=device_id,
        device_name=body.device_name,
        invite_code=invite.invite_code,
        role_level=invite.role_level,
        bind_time=now,
        last_online_time=now,
        status=1,
    )
    invite.used_count += 1
    db.add(device)
    db.commit()
    db.refresh(device)
    auth_cache.set_device(device.device_id, device.role_level)
    return device_response(device)


@router.get("/me", response_model=DeviceResponse)
def get_my_device(device: CurrentDevice):
    """已绑定设备启动时读取权限，不依赖本地缓存判断角色。"""
    return device_response(device)


@router.post("/heartbeat", response_model=HeartbeatResponse)
def heartbeat(device: CurrentDevice, db: DbSession):
    """心跳更新在线时间，可用于桌面托盘/移动端后台保活监控。"""
    now = datetime.now()
    device.last_online_time = now
    db.commit()
    auth_cache.set_device(device.device_id, device.role_level)
    return HeartbeatResponse(device_id=device.device_id, role_level=device.role_level, server_time=now)
