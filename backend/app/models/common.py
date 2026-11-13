from datetime import datetime

from sqlalchemy import DateTime, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column


class BusinessRecordMixin:
    """四张业务表共有的固定字段；字段类型和长度与强制 SQL 一致。"""

    record_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    creator_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now()
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, server_default=func.now(), onupdate=datetime.now
    )
    data_status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, server_default="1", index=True)
