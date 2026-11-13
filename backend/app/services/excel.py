from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, Optional, Type

from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pydantic import ValidationError
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.core.security import new_id
from app.models import Device, PersonalInspiration, PropertySale, TenancyLease, WorkLog
from app.schemas.inspiration import InspirationCreate
from app.schemas.lease import TenancyLeaseCreate
from app.schemas.sale import PropertySaleCreate
from app.schemas.work import WorkLogCreate
from app.services.query_utils import apply_period_filter
from app.services.record_utils import (
    MODULE_MODELS,
    apply_payload,
    ensure_can_edit,
    find_duplicates,
    log_operation,
    scope_condition,
    serialize_record,
)

FIELD_LABELS = {
    PropertySale: {
        "record_id": "记录ID",
        "creator_id": "创建设备ID",
        "create_time": "创建时间",
        "update_time": "更新时间",
        "data_status": "数据状态",
        "tags": "标签",
        "ext_field_1": "扩展字段1",
        "ext_field_2": "扩展字段2",
        "ext_field_3": "扩展字段3",
        "ext_field_4": "扩展字段4",
        "ext_field_5": "扩展字段5",
        "project_name": "项目名称",
        "district": "所在区域",
        "address": "详细地址",
        "total_area": "总建筑面积",
        "standard_floor_area": "标准层面积",
        "total_floors": "总楼层",
        "property_grade": "物业等级",
        "project_feature": "项目核心特点",
        "deal_date": "交易时间",
        "deal_total_price": "交易总价（万元）",
        "deal_unit_price": "成交单价（元/㎡）",
        "deal_type": "交易方式",
        "deal_target": "交易标的",
        "deal_status": "交易状态",
        "seller": "原业主方",
        "buyer": "受让方（买家）",
        "buyer_purpose": "买家购置用途",
        "has_intermediary": "是否有居间",
        "main_intermediary": "主居间方",
        "joint_intermediary": "联合居间方",
        "commission_remark": "佣金备注",
        "deal_background": "交易背景",
        "inside_story": "内部趣事/传闻",
        "remark": "通用备注",
    },
    TenancyLease: {
        "record_id": "记录ID",
        "creator_id": "创建设备ID",
        "create_time": "创建时间",
        "update_time": "更新时间",
        "data_status": "数据状态",
        "tags": "标签",
        "ext_field_1": "扩展字段1",
        "ext_field_2": "扩展字段2",
        "ext_field_3": "扩展字段3",
        "ext_field_4": "扩展字段4",
        "ext_field_5": "扩展字段5",
        "company_name": "企业名称",
        "industry": "所属行业",
        "company_scale": "企业规模",
        "old_project": "原办公项目",
        "old_area": "原租赁面积",
        "old_expire_date": "原租约到期时间",
        "new_project": "新办公项目",
        "new_area": "新租赁面积",
        "floor": "所在楼层",
        "lease_type": "租赁类型",
        "rent_price": "租金单价",
        "property_fee": "物业费标准",
        "rent_free_period": "免租期（月）",
        "lease_term": "签约年限（年）",
        "start_date": "起租日期",
        "end_date": "到期日期",
        "rent_increase": "租金递增",
        "main_intermediary": "主居间方",
        "joint_intermediary": "联合居间方",
        "broker_name": "经办经纪人",
        "move_reason": "搬迁原因",
        "company_background": "企业动态背景",
        "remark": "通用备注",
    },
    WorkLog: {
        "record_id": "记录ID",
        "creator_id": "创建设备ID",
        "create_time": "创建时间",
        "update_time": "更新时间",
        "data_status": "数据状态",
        "tags": "标签",
        "ext_field_1": "执行情况/完成说明",
        "ext_field_2": "推迟记录（JSON）",
        "ext_field_3": "扩展数值",
        "ext_field_4": "计划执行具体时分",
        "ext_field_5": "计划状态",
        "record_type": "记录类型",
        "record_date": "记录日期",
        "content": "记录正文",
        "todo_items": "待办事项",
        "related_project": "关联项目",
        "follow_status": "跟进状态",
        "is_shared": "是否共享",
    },
    PersonalInspiration: {
        "record_id": "记录ID",
        "creator_id": "创建设备ID",
        "create_time": "创建时间",
        "update_time": "更新时间",
        "data_status": "数据状态",
        "tags": "标签",
        "ext_field_1": "扩展字段1",
        "ext_field_2": "扩展字段2",
        "ext_field_3": "扩展字段3",
        "ext_field_4": "扩展字段4",
        "ext_field_5": "扩展字段5",
        "inspiration_type": "灵感类型",
        "record_time": "记录时间",
        "content": "灵感正文",
    },
}

PLAN_STATUS = {0: "未做", 1: "正在做", 2: "已做好", 3: "计划搁置"}
PLAN_STATUS_REVERSE = {value: key for key, value in PLAN_STATUS.items()}
SCHEMAS = {
    PropertySale: PropertySaleCreate,
    TenancyLease: TenancyLeaseCreate,
    WorkLog: WorkLogCreate,
    PersonalInspiration: InspirationCreate,
}
DATE_COLUMN_NAMES = {"deal_date", "start_date", "end_date", "old_expire_date", "record_date", "record_time"}
INTERNAL_IMPORT_FIELDS = {"record_id", "creator_id", "create_time", "update_time", "data_status"}


def module_model(module: str) -> Type:
    if module not in MODULE_MODELS:
        raise HTTPException(status_code=422, detail="不支持的业务模块")
    return MODULE_MODELS[module]


def build_export_query(
    module: str,
    device: Device,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period_type: Optional[str] = None,
    period_value: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Select:
    """复用与列表一致的权限范围，确保导出不能绕过数据隔离。"""
    model = module_model(module)
    query = select(model).where(model.data_status == 1)
    if model is WorkLog:
        query = query.where(scope_condition(WorkLog, device))
    elif model is PersonalInspiration:
        query = query.where(scope_condition(PersonalInspiration, device))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        if model is PropertySale:
            query = query.where(or_(PropertySale.project_name.like(pattern), PropertySale.district.like(pattern)))
        elif model is TenancyLease:
            query = query.where(or_(TenancyLease.company_name.like(pattern), TenancyLease.new_project.like(pattern)))
        else:
            query = query.where(model.content.like(pattern))
    date_field = {
        PropertySale: PropertySale.deal_date,
        TenancyLease: TenancyLease.start_date,
        WorkLog: WorkLog.record_date,
        PersonalInspiration: PersonalInspiration.record_time,
    }[model]
    if start_date:
        query = query.where(date_field >= start_date)
    if end_date:
        query = query.where(date_field <= end_date)
    return apply_period_filter(query, date_field, period_type, period_value)


def format_cell(model: Type, field: str, value: Any) -> Any:
    if value is None:
        return None
    if field == "commission_remark" and model is PropertySale:
        return value
    if model is WorkLog and field == "ext_field_5":
        return PLAN_STATUS.get(value, value)
    if model is WorkLog and field == "is_shared":
        return "是" if value == 1 else "否"
    if field == "data_status":
        return "正常" if value == 1 else "已删除"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def make_excel(model: Type, records: list[Any], device: Device, sheet_name: str) -> BytesIO:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name[:31]
    columns = [column.name for column in model.__table__.columns]
    labels = FIELD_LABELS[model]
    headers = [labels.get(column, column) for column in columns]
    sheet.append(headers)

    header_fill = PatternFill("solid", fgColor="444444")
    header_font = Font(color="FFFFFF", bold=True, name="微软雅黑", size=10)
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for cell in sheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    for record in records:
        serialized = serialize_record(record, device)
        sheet.append([format_cell(model, column, serialized.get(column)) for column in columns])
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="微软雅黑", size=10)
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=False)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for index, header in enumerate(headers, start=1):
        max_len = len(str(header))
        for cell in sheet[get_column_letter(index)][1:51]:
            max_len = max(max_len, len(str(cell.value or "")))
        sheet.column_dimensions[get_column_letter(index)].width = min(max(max_len + 2, 10), 40)
    sheet.row_dimensions[1].height = 24
    for row_index in range(2, sheet.max_row + 1):
        sheet.row_dimensions[row_index].height = 22
    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)
    return stream


def parse_excel_rows(content: bytes, model: Type) -> list[dict[str, Any]]:
    """只接受中文表头；空行跳过，未知列忽略并在返回中计数。"""
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="无法读取 Excel 文件") from exc
    sheet = workbook.active
    headers = [str(cell.value).strip() if cell.value is not None else "" for cell in next(sheet.iter_rows(max_row=1))]
    label_to_field = {label: field for field, label in FIELD_LABELS[model].items()}
    mapped = [(index, label_to_field.get(header)) for index, header in enumerate(headers)]
    if not any(field for _, field in mapped):
        raise HTTPException(status_code=422, detail="没有识别到本模块的中文表头")
    rows: list[dict[str, Any]] = []
    for values in sheet.iter_rows(min_row=2, values_only=True):
        if not any(value not in (None, "") for value in values):
            continue
        row: dict[str, Any] = {}
        for index, field in mapped:
            if not field or field in INTERNAL_IMPORT_FIELDS:
                continue
            value = values[index] if index < len(values) else None
            if field in DATE_COLUMN_NAMES and isinstance(value, datetime):
                value = value.date() if field != "record_time" else value
            if model is WorkLog and field == "ext_field_5" and isinstance(value, str):
                value = PLAN_STATUS_REVERSE.get(value, value)
            if model is WorkLog and field == "is_shared" and isinstance(value, str):
                value = 1 if value.strip() in {"是", "1", "共享"} else 0
            row[field] = value
        rows.append(row)
    return rows


def import_excel_rows(
    db: Session,
    device: Device,
    module: str,
    rows: list[dict[str, Any]],
    duplicate_action: str,
    request_ip: Optional[str] = None,
) -> dict[str, Any]:
    """Excel 永不静默覆盖：重复时由 duplicate_action 明确决定。"""
    if duplicate_action not in {"overwrite", "skip", "create_new"}:
        raise HTTPException(status_code=422, detail="duplicate_action 必须是 overwrite/skip/create_new")
    model = module_model(module)
    schema = SCHEMAS[model]
    created = 0
    overwritten = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        try:
            validated = schema(**row)
            payload = validated.model_dump()
            duplicates = find_duplicates(db, model, payload) if model in {PropertySale, TenancyLease} else []
            if duplicates and duplicate_action == "skip":
                skipped += 1
                continue
            if duplicates and duplicate_action == "overwrite":
                target = duplicates[0]
                ensure_can_edit(target, device)
                apply_payload(target, payload)
                overwritten += 1
                continue
            record = model(record_id=new_id(), creator_id=device.device_id, data_status=1)
            apply_payload(record, payload)
            db.add(record)
            created += 1
        except (ValidationError, ValueError, HTTPException) as exc:
            message = str(getattr(exc, "detail", exc))
            errors.append({"row": index, "error": message})
    log_operation(
        db,
        device.device_id,
        "add",
        module,
        None,
        {"operation": "excel_import", "created": created, "overwritten": overwritten, "skipped": skipped, "errors": len(errors)},
        request_ip,
    )
    db.commit()
    return {
        "module": module,
        "duplicate_action": duplicate_action,
        "created": created,
        "overwritten": overwritten,
        "skipped": skipped,
        "failed": len(errors),
        "errors": errors[:100],
    }


def preview_excel_rows(db: Session, module: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """导入前预检：返回有效行、重复行与错误行，不写入数据库。"""
    model = module_model(module)
    schema = SCHEMAS[model]
    duplicates: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    valid_rows = 0
    for index, row in enumerate(rows, start=2):
        try:
            validated = schema(**row)
            payload = validated.model_dump()
            matched = find_duplicates(db, model, payload) if model in {PropertySale, TenancyLease} else []
            valid_rows += 1
            if matched:
                duplicates.append(
                    {
                        "row": index,
                        "summary": payload.get("project_name")
                        or payload.get("company_name")
                        or (payload.get("content") or "")[:80],
                        "existing_ids": [item.record_id for item in matched[:10]],
                    }
                )
        except (ValidationError, ValueError) as exc:
            errors.append({"row": index, "error": str(exc)})
    return {
        "module": module,
        "total_rows": len(rows),
        "valid_rows": valid_rows,
        "duplicate_count": len(duplicates),
        "duplicates": duplicates[:100],
        "error_count": len(errors),
        "errors": errors[:100],
    }
