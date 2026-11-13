from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class InspirationCreate(BaseModel):
    tags: Optional[str] = Field(default=None, max_length=255)
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[date] = None
    ext_field_5: Optional[int] = None
    inspiration_type: Optional[str] = Field(default=None, max_length=20)
    record_time: datetime
    content: str = Field(min_length=1)


class InspirationUpdate(BaseModel):
    tags: Optional[str] = Field(default=None, max_length=255)
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[date] = None
    ext_field_5: Optional[int] = None
    inspiration_type: Optional[str] = Field(default=None, max_length=20)
    record_time: Optional[datetime] = None
    content: Optional[str] = None
