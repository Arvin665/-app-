from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class PropertySaleCreate(BaseModel):
    """买卖记录录入字段；可选字段允许语音识别后暂缺。"""

    tags: Optional[str] = Field(default=None, max_length=255)
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[date] = None
    ext_field_5: Optional[int] = None
    project_name: str = Field(min_length=1, max_length=100)
    district: str = Field(min_length=1, max_length=50)
    address: Optional[str] = Field(default=None, max_length=255)
    total_area: Optional[Decimal] = None
    standard_floor_area: Optional[Decimal] = None
    total_floors: Optional[str] = Field(default=None, max_length=20)
    property_grade: Optional[str] = Field(default=None, max_length=20)
    project_feature: Optional[str] = None
    deal_date: date
    deal_total_price: Optional[Decimal] = None
    deal_unit_price: Optional[Decimal] = None
    deal_type: Optional[str] = Field(default=None, max_length=20)
    deal_target: Optional[str] = Field(default=None, max_length=50)
    deal_status: str = Field(default="已签约", max_length=20)
    seller: Optional[str] = Field(default=None, max_length=100)
    buyer: Optional[str] = Field(default=None, max_length=100)
    buyer_purpose: Optional[str] = Field(default=None, max_length=50)
    has_intermediary: Optional[str] = Field(default=None, max_length=10)
    main_intermediary: Optional[str] = Field(default=None, max_length=100)
    joint_intermediary: Optional[str] = Field(default=None, max_length=255)
    commission_remark: Optional[str] = None
    deal_background: Optional[str] = None
    inside_story: Optional[str] = None
    remark: Optional[str] = None


class PropertySaleUpdate(BaseModel):
    """局部更新模型；服务端按 exclude_unset 只写用户明确提交的字段。"""

    tags: Optional[str] = None
    ext_field_1: Optional[str] = None
    ext_field_2: Optional[str] = None
    ext_field_3: Optional[Decimal] = None
    ext_field_4: Optional[date] = None
    ext_field_5: Optional[int] = None
    project_name: Optional[str] = Field(default=None, max_length=100)
    district: Optional[str] = Field(default=None, max_length=50)
    address: Optional[str] = Field(default=None, max_length=255)
    total_area: Optional[Decimal] = None
    standard_floor_area: Optional[Decimal] = None
    total_floors: Optional[str] = Field(default=None, max_length=20)
    property_grade: Optional[str] = Field(default=None, max_length=20)
    project_feature: Optional[str] = None
    deal_date: Optional[date] = None
    deal_total_price: Optional[Decimal] = None
    deal_unit_price: Optional[Decimal] = None
    deal_type: Optional[str] = Field(default=None, max_length=20)
    deal_target: Optional[str] = Field(default=None, max_length=50)
    deal_status: Optional[str] = Field(default=None, max_length=20)
    seller: Optional[str] = Field(default=None, max_length=100)
    buyer: Optional[str] = Field(default=None, max_length=100)
    buyer_purpose: Optional[str] = Field(default=None, max_length=50)
    has_intermediary: Optional[str] = Field(default=None, max_length=10)
    main_intermediary: Optional[str] = Field(default=None, max_length=100)
    joint_intermediary: Optional[str] = Field(default=None, max_length=255)
    commission_remark: Optional[str] = None
    deal_background: Optional[str] = None
    inside_story: Optional[str] = None
    remark: Optional[str] = None
