from datetime import date
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentDevice, DbSession
from app.services.excel import (
    build_export_query,
    import_excel_rows,
    make_excel,
    module_model,
    parse_excel_rows,
    preview_excel_rows,
)
from app.services.record_utils import MODULE_NAMES, log_operation

router = APIRouter(prefix="/transfer", tags=["Excel 导入导出"])


@router.get("/export/{module}")
def export_excel(
    module: str,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    period_type: Optional[str] = Query(default=None, pattern=r"^(day|week|month|quarter|year)$"),
    period_value: Optional[str] = None,
    keyword: Optional[str] = None,
):
    """导出母表字段；普通成员的佣金备注自动置空。"""
    model = module_model(module)
    query = build_export_query(module, device, start_date, end_date, period_type, period_value, keyword)
    records = list(db.scalars(query.order_by(model.create_time.desc())).all())
    stream = make_excel(model, records, device, MODULE_NAMES[module])
    log_operation(
        db,
        device.device_id,
        "export",
        module,
        None,
        {"operation": "excel_export", "rows": len(records), "sensitive_visible": device.role_level == 1},
        request.client.host if request.client else None,
    )
    db.commit()
    filename = f"{MODULE_NAMES[module]}_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/import/preview/{module}")
async def preview_import(
    module: str,
    db: DbSession,
    device: CurrentDevice,
    file: UploadFile = File(...),
):
    """只预检不入库，桌面端据此先提示重复、跳过或覆盖。"""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="仅支持 .xlsx 文件")
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Excel 文件不能超过 50MB")
    model = module_model(module)
    rows = parse_excel_rows(content, model)
    if not rows:
        raise HTTPException(status_code=422, detail="Excel 中没有可导入的数据")
    return preview_excel_rows(db, module, rows)


@router.post("/import/{module}")
async def import_excel(
    module: str,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
    duplicate_action: str = Form(...),
    file: UploadFile = File(...),
):
    """导入前必须选择重复处理方式：覆盖、跳过或另存为新记录。"""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="仅支持 .xlsx 文件")
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Excel 文件不能超过 50MB")
    model = module_model(module)
    rows = parse_excel_rows(content, model)
    if not rows:
        raise HTTPException(status_code=422, detail="Excel 中没有可导入的数据")
    return import_excel_rows(
        db,
        device,
        module,
        rows,
        duplicate_action,
        request.client.host if request.client else None,
    )
