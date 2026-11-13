from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BindRequest(BaseModel):
    """首次设备绑定请求；邀请码与设备信息必须同时提交。"""

    invite_code: str = Field(min_length=6, max_length=6)
    device_id: str = Field(min_length=32, max_length=32)
    device_name: Optional[str] = Field(default=None, max_length=100)

    @field_validator("invite_code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("邀请码必须是 6 位数字")
        return value


class DeviceResponse(BaseModel):
    device_id: str
    device_name: Optional[str] = None
    invite_code: Optional[str] = None
    role_level: int
    role_name: str
    bind_time: datetime
    last_online_time: Optional[datetime] = None
    status: int
    permissions: list[str]


class HeartbeatResponse(BaseModel):
    device_id: str
    role_level: int
    server_time: datetime
    status: str = "online"


class InviteCreateRequest(BaseModel):
    valid_start: Optional[datetime] = None
    valid_end: Optional[datetime] = None
    max_use_count: int = Field(default=10, ge=1, le=10000)
    role_level: int = Field(default=2, ge=1, le=2)
