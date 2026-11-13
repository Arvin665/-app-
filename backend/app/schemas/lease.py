from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TenancyLeaseCreate(BaseModel):
    tags: Optional[str] = Field(default=None, max_length=255)
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[date] = None
    ext_field_5: Optional[int] = None
    company_name: str = Field(min_length=1, max_length=100)
    industry: Optional[str] = Field(default=None, max_length=50)
    company_scale: Optional[str] = Field(default=None, max_length=50)
    old_project: Optional[str] = Field(default=None, max_length=100)
    old_area: Optional[Decimal] = None
    old_expire_date: Optional[date] = None
    new_project: str = Field(min_length=1, max_length=100)
    new_area: Optional[Decimal] = None
    floor: Optional[str] = Field(default=None, max_length=50)
    lease_type: str = Field(min_length=1, max_length=20)
    rent_price: Optional[Decimal] = None
    property_fee: Optional[Decimal] = None
    rent_free_period: Optional[int] = None
    lease_term: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_increase: Optional[str] = Field(default=None, max_length=50)
    main_intermediary: Optional[str] = Field(default=None, max_length=100)
    joint_intermediary: Optional[str] = Field(default=None, max_length=255)
    broker_name: Optional[str] = Field(default=None, max_length=50)
    move_reason: Optional[str] = None
    company_background: Optional[str] = None
    remark: Optional[str] = None


class TenancyLeaseUpdate(BaseModel):
    tags: Optional[str] = Field(default=None, max_length=255)
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[date] = None
    ext_field_5: Optional[int] = None
    company_name: Optional[str] = Field(default=None, max_length=100)
    industry: Optional[str] = Field(default=None, max_length=50)
    company_scale: Optional[str] = Field(default=None, max_length=50)
    old_project: Optional[str] = Field(default=None, max_length=100)
    old_area: Optional[Decimal] = None
    old_expire_date: Optional[date] = None
    new_project: Optional[str] = Field(default=None, max_length=100)
    new_area: Optional[Decimal] = None
    floor: Optional[str] = Field(default=None, max_length=50)
    lease_type: Optional[str] = Field(default=None, max_length=20)
    rent_price: Optional[Decimal] = None
    property_fee: Optional[Decimal] = None
    rent_free_period: Optional[int] = None
    lease_term: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    rent_increase: Optional[str] = Field(default=None, max_length=50)
    main_intermediary: Optional[str] = Field(default=None, max_length=100)
    joint_intermediary: Optional[str] = Field(default=None, max_length=255)
    broker_name: Optional[str] = Field(default=None, max_length=50)
    move_reason: Optional[str] = None
    company_background: Optional[str] = None
    remark: Optional[str] = None
