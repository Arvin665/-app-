from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, SmallInteger, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.security import decrypt_sensitive, encrypt_sensitive
from app.db.base import Base
from app.models.common import BusinessRecordMixin
from app.models.system import MYSQL_OPTIONS


class PropertySale(BusinessRecordMixin, Base):
    """项目买卖信息表，字段严格对应初始化 SQL。"""

    __tablename__ = "biz_property_sale"
    __table_args__ = MYSQL_OPTIONS

    tags: Mapped[Optional[str]] = mapped_column(String(255))
    ext_field_1: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_2: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_3: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    ext_field_4: Mapped[Optional[date]] = mapped_column(Date)
    ext_field_5: Mapped[Optional[int]] = mapped_column(Integer)
    project_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(String(255))
    total_area: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    standard_floor_area: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    total_floors: Mapped[Optional[str]] = mapped_column(String(20))
    property_grade: Mapped[Optional[str]] = mapped_column(String(20))
    project_feature: Mapped[Optional[str]] = mapped_column(Text)
    deal_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    deal_total_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    deal_unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    deal_type: Mapped[Optional[str]] = mapped_column(String(20))
    deal_target: Mapped[Optional[str]] = mapped_column(String(50))
    deal_status: Mapped[str] = mapped_column(String(20), nullable=False, default="已签约", server_default="已签约")
    seller: Mapped[Optional[str]] = mapped_column(String(100))
    buyer: Mapped[Optional[str]] = mapped_column(String(100))
    buyer_purpose: Mapped[Optional[str]] = mapped_column(String(50))
    has_intermediary: Mapped[Optional[str]] = mapped_column(String(10))
    main_intermediary: Mapped[Optional[str]] = mapped_column(String(100))
    joint_intermediary: Mapped[Optional[str]] = mapped_column(String(255))
    commission_remark: Mapped[Optional[str]] = mapped_column(Text)
    deal_background: Mapped[Optional[str]] = mapped_column(Text)
    inside_story: Mapped[Optional[str]] = mapped_column(Text)
    remark: Mapped[Optional[str]] = mapped_column(Text)

    @property
    def decrypted_commission_remark(self) -> Optional[str]:
        """应用层只向有权限的序列化逻辑提供明文。"""
        return decrypt_sensitive(self.commission_remark)

    def set_commission_remark(self, value: Optional[str]) -> None:
        """写入前完成对称加密，数据库不落明文。"""
        self.commission_remark = encrypt_sensitive(value)


class TenancyLease(BusinessRecordMixin, Base):
    """企业租赁信息表，字段严格对应初始化 SQL。"""

    __tablename__ = "biz_tenancy_lease"
    __table_args__ = MYSQL_OPTIONS

    tags: Mapped[Optional[str]] = mapped_column(String(255))
    ext_field_1: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_2: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_3: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    ext_field_4: Mapped[Optional[date]] = mapped_column(Date)
    ext_field_5: Mapped[Optional[int]] = mapped_column(Integer)
    company_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    industry: Mapped[Optional[str]] = mapped_column(String(50))
    company_scale: Mapped[Optional[str]] = mapped_column(String(50))
    old_project: Mapped[Optional[str]] = mapped_column(String(100))
    old_area: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    old_expire_date: Mapped[Optional[date]] = mapped_column(Date)
    new_project: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    new_area: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    floor: Mapped[Optional[str]] = mapped_column(String(50))
    lease_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rent_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    property_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    rent_free_period: Mapped[Optional[int]] = mapped_column(Integer)
    lease_term: Mapped[Optional[int]] = mapped_column(Integer)
    start_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    rent_increase: Mapped[Optional[str]] = mapped_column(String(50))
    main_intermediary: Mapped[Optional[str]] = mapped_column(String(100))
    joint_intermediary: Mapped[Optional[str]] = mapped_column(String(255))
    broker_name: Mapped[Optional[str]] = mapped_column(String(50))
    move_reason: Mapped[Optional[str]] = mapped_column(Text)
    company_background: Mapped[Optional[str]] = mapped_column(Text)
    remark: Mapped[Optional[str]] = mapped_column(Text)


class WorkLog(BusinessRecordMixin, Base):
    """工作记录与待办计划共用一张表，通过 record_type 区分。"""

    __tablename__ = "biz_work_log"
    __table_args__ = MYSQL_OPTIONS

    tags: Mapped[Optional[str]] = mapped_column(String(255))
    ext_field_1: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_2: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_3: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    ext_field_4: Mapped[Optional[str]] = mapped_column(String(10))
    ext_field_5: Mapped[Optional[int]] = mapped_column(Integer)
    record_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    todo_items: Mapped[Optional[str]] = mapped_column(Text)
    related_project: Mapped[Optional[str]] = mapped_column(String(255))
    follow_status: Mapped[Optional[str]] = mapped_column(String(20))
    is_shared: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default="0")


class PersonalInspiration(BusinessRecordMixin, Base):
    """个人灵感角，即使管理员也不能跨设备读取。"""

    __tablename__ = "biz_personal_inspiration"
    __table_args__ = MYSQL_OPTIONS

    tags: Mapped[Optional[str]] = mapped_column(String(255))
    ext_field_1: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_2: Mapped[Optional[str]] = mapped_column(Text)
    ext_field_3: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    ext_field_4: Mapped[Optional[date]] = mapped_column(Date)
    ext_field_5: Mapped[Optional[int]] = mapped_column(Integer)
    inspiration_type: Mapped[Optional[str]] = mapped_column(String(20))
    record_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
