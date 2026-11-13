from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field

RECORD_TYPES = Literal[
    "每日心得",
    "客户跟进",
    "踩盘记录",
    "周计划",
    "周总结",
    "月计划",
    "月总结",
    "业务规划",
    "待办计划",
    "每日复盘",
]


class WorkLogCreate(BaseModel):
    tags: Optional[str] = Field(default=None, max_length=255)
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    ext_field_5: Optional[int] = Field(default=None, ge=0, le=3)
    record_type: RECORD_TYPES
    record_date: date
    content: str = Field(min_length=1)
    todo_items: Optional[str] = None
    related_project: Optional[str] = Field(default=None, max_length=255)
    follow_status: Optional[str] = Field(default=None, max_length=20)
    is_shared: int = Field(default=0, ge=0, le=1)


class WorkLogUpdate(BaseModel):
    tags: Optional[str] = Field(default=None, max_length=255)
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    ext_field_5: Optional[int] = Field(default=None, ge=0, le=3)
    record_type: Optional[RECORD_TYPES] = None
    record_date: Optional[date] = None
    content: Optional[str] = None
    todo_items: Optional[str] = None
    related_project: Optional[str] = Field(default=None, max_length=255)
    follow_status: Optional[str] = Field(default=None, max_length=20)
    is_shared: Optional[int] = Field(default=None, ge=0, le=1)


class PlanStatusRequest(BaseModel):
    status: int = Field(ge=0, le=3)
    note: Optional[str] = None


class PlanPostponeRequest(BaseModel):
    new_date: date
    new_time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    reason: str = Field(min_length=1, max_length=500)


class DailyArchiveRequest(BaseModel):
    record_date: date
    insight: Optional[str] = None
