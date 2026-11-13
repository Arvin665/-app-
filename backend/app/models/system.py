from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


MYSQL_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_unicode_ci",
}


class InviteCode(Base):
    """管理员签发的一次性或限量邀请码。"""

    __tablename__ = "sys_invite_code"
    __table_args__ = MYSQL_OPTIONS

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    invite_code: Mapped[str] = mapped_column(String(6), nullable=False, unique=True, index=True)
    valid_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    valid_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    max_use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=10, server_default="10")
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    role_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2, server_default="2")
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    creator_id: Mapped[str] = mapped_column(String(32), nullable=False)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now()
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now(), onupdate=datetime.now
    )


class Device(Base):
    """设备即用户；不保存账号密码，以 device_id 识别成员。"""

    __tablename__ = "sys_device"
    __table_args__ = MYSQL_OPTIONS

    device_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(100))
    invite_code: Mapped[Optional[str]] = mapped_column(String(6))
    role_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=2, server_default="2")
    bind_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now()
    )
    last_online_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now(), onupdate=datetime.now
    )


class OperationLog(Base):
    """全量增删改与导出的审计轨迹。"""

    __tablename__ = "sys_operation_log"
    __table_args__ = MYSQL_OPTIONS

    log_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    biz_module: Mapped[str] = mapped_column(String(20), nullable=False)
    biz_record_id: Mapped[Optional[str]] = mapped_column(String(32))
    operation_content: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now()
    )


class Attachment(Base):
    """业务附件元数据和对象存储地址。"""

    __tablename__ = "sys_attachment"
    __table_args__ = MYSQL_OPTIONS

    attach_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    biz_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    biz_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger)
    file_url: Mapped[str] = mapped_column(String(255), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(255))
    ocr_content: Mapped[Optional[str]] = mapped_column(Text)
    uploader_id: Mapped[str] = mapped_column(String(32), nullable=False)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now()
    )
    data_status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1")
