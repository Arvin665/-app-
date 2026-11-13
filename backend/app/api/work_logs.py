import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select

from app.api.deps import CurrentDevice, DbSession
from app.core.security import new_id
from app.models import WorkLog
from app.schemas.work import (
    DailyArchiveRequest,
    PlanPostponeRequest,
    PlanStatusRequest,
    WorkLogCreate,
    WorkLogUpdate,
)
from app.services.query_utils import apply_period_filter
from app.services.record_utils import (
    apply_payload,
    apply_soft_delete_scope,
    ensure_can_edit,
    get_record_or_404,
    log_operation,
    scope_condition,
    serialize_record,
)

router = APIRouter(prefix="/work-logs", tags=["工作记录与待办计划"])
PLAN_STATUS_NAMES = {0: "未做", 1: "正在做", 2: "已做好", 3: "计划搁置"}


def review_exists(db: DbSession, device_id: str, record_date: date) -> bool:
    review = db.scalar(
        select(WorkLog).where(
            WorkLog.creator_id == device_id,
            WorkLog.record_date == record_date,
            WorkLog.record_type == "每日复盘",
            WorkLog.data_status == 1,
        )
    )
    return review is not None


def ensure_plan_mutable(db: DbSession, record: WorkLog, device_id: str) -> None:
    if record.record_type != "待办计划":
        raise HTTPException(status_code=422, detail="该记录不是待办计划")
    if review_exists(db, device_id, record.record_date):
        raise HTTPException(status_code=409, detail="该日计划已归档锁定，不能再修改状态")


@router.get("")
def list_work_logs(
    db: DbSession,
    device: CurrentDevice,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    keyword: Optional[str] = None,
    record_type: Optional[str] = None,
    record_date: Optional[date] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    follow_status: Optional[str] = None,
    plan_status: Optional[int] = Query(default=None, ge=0, le=3),
    is_shared: Optional[int] = Query(default=None, ge=0, le=1),
    period_type: Optional[str] = Query(default=None, pattern=r"^(day|week|month|quarter|year)$"),
    period_value: Optional[str] = None,
):
    """默认返回本人记录与团队共享记录；私有工作记录不暴露给管理员。"""
    query = apply_soft_delete_scope(select(WorkLog), WorkLog).where(scope_condition(WorkLog, device))
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(
            or_(WorkLog.content.like(pattern), WorkLog.todo_items.like(pattern), WorkLog.related_project.like(pattern))
        )
    if record_type:
        query = query.where(WorkLog.record_type == record_type)
    if record_date:
        query = query.where(WorkLog.record_date == record_date)
    if start_date:
        query = query.where(WorkLog.record_date >= start_date)
    if end_date:
        query = query.where(WorkLog.record_date <= end_date)
    if follow_status:
        query = query.where(WorkLog.follow_status == follow_status)
    if plan_status is not None:
        query = query.where(WorkLog.ext_field_5 == plan_status)
    if is_shared is not None:
        query = query.where(WorkLog.is_shared == is_shared)
    query = apply_period_filter(query, WorkLog.record_date, period_type, period_value)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    records = db.scalars(
        query.order_by(WorkLog.record_date.desc(), WorkLog.ext_field_4.desc().nullslast(), WorkLog.update_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": [serialize_record(record, device) for record in records], "total": total, "page": page, "page_size": page_size}


@router.get("/plans")
def list_daily_plans(
    db: DbSession,
    device: CurrentDevice,
    record_date: Optional[date] = None,
    include_archived: bool = False,
):
    """待办计划按天查询，只允许读取本人创建的私有计划。"""
    target_date = record_date or date.today()
    query = select(WorkLog).where(
        WorkLog.creator_id == device.device_id,
        WorkLog.record_type == "待办计划",
        WorkLog.record_date == target_date,
        WorkLog.data_status == 1,
    )
    records = list(db.scalars(query.order_by(WorkLog.ext_field_4.asc().nullsfirst())).all())
    return {
        "record_date": target_date.isoformat(),
        "locked": review_exists(db, device.device_id, target_date),
        "items": [serialize_record(record, device) for record in records],
        "include_archived": include_archived,
    }


@router.get("/{record_id}")
def get_work_log(record_id: str, db: DbSession, device: CurrentDevice):
    return serialize_record(get_record_or_404(db, WorkLog, record_id, device), device)


@router.post("", status_code=201)
def create_work_log(body: WorkLogCreate, db: DbSession, device: CurrentDevice, request: Request):
    payload = body.model_dump()
    if payload["record_type"] == "待办计划" and payload.get("ext_field_5") is None:
        payload["ext_field_5"] = 0
    record = WorkLog(record_id=new_id(), creator_id=device.device_id, data_status=1)
    apply_payload(record, payload)
    db.add(record)
    log_operation(
        db,
        device.device_id,
        "add",
        "work",
        record.record_id,
        {"record_type": record.record_type, "record_date": str(record.record_date)},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.patch("/{record_id}")
def update_work_log(
    record_id: str,
    body: WorkLogUpdate,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    record = get_record_or_404(db, WorkLog, record_id, device)
    ensure_can_edit(record, device)
    if record.record_type == "待办计划" and review_exists(db, device.device_id, record.record_date):
        raise HTTPException(status_code=409, detail="该日计划已归档锁定")
    changes = apply_payload(record, body.model_dump(exclude_unset=True))
    log_operation(
        db,
        device.device_id,
        "update",
        "work",
        record.record_id,
        {"changed_fields": sorted(changes.keys())},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.delete("/{record_id}")
def delete_work_log(record_id: str, db: DbSession, device: CurrentDevice, request: Request):
    record = get_record_or_404(db, WorkLog, record_id, device)
    ensure_can_edit(record, device)
    record.data_status = 0
    log_operation(
        db,
        device.device_id,
        "delete",
        "work",
        record.record_id,
        {"record_type": record.record_type},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"record_id": record_id, "deleted": True, "recycle_days": 7}


@router.post("/{record_id}/status")
def update_plan_status(
    record_id: str,
    body: PlanStatusRequest,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    """固定四态流转，状态说明写入 ext_field_1，操作日志保留每次轨迹。"""
    record = get_record_or_404(db, WorkLog, record_id, device)
    ensure_can_edit(record, device)
    ensure_plan_mutable(db, record, device.device_id)
    previous = record.ext_field_5
    record.ext_field_5 = body.status
    if body.note:
        note_line = f"[{datetime.now():%Y-%m-%d %H:%M}] {PLAN_STATUS_NAMES[body.status]}：{body.note.strip()}"
        record.ext_field_1 = f"{record.ext_field_1}\n{note_line}".strip() if record.ext_field_1 else note_line
    log_operation(
        db,
        device.device_id,
        "update",
        "work",
        record.record_id,
        {"status_from": previous, "status_to": body.status, "note": body.note},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.post("/{record_id}/postpone")
def postpone_plan(
    record_id: str,
    body: PlanPostponeRequest,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    """每次推迟追加 JSON 历史；前端据此取消旧提醒并重设新提醒。"""
    record = get_record_or_404(db, WorkLog, record_id, device)
    ensure_can_edit(record, device)
    ensure_plan_mutable(db, record, device.device_id)
    try:
        history = json.loads(record.ext_field_2) if record.ext_field_2 else []
    except json.JSONDecodeError:
        history = []
    history.append(
        {
            "from_date": record.record_date.isoformat(),
            "from_time": record.ext_field_4,
            "to_date": body.new_date.isoformat(),
            "to_time": body.new_time,
            "reason": body.reason,
            "postponed_at": datetime.now().isoformat(timespec="seconds"),
            "device_id": device.device_id,
        }
    )
    record.ext_field_2 = json.dumps(history, ensure_ascii=False)
    record.record_date = body.new_date
    record.ext_field_4 = body.new_time
    log_operation(
        db,
        device.device_id,
        "update",
        "work",
        record.record_id,
        {"operation": "postpone", "to_date": body.new_date.isoformat(), "to_time": body.new_time, "reason": body.reason},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(record)
    return serialize_record(record, device)


@router.post("/archive-daily")
def archive_daily_plan(
    body: DailyArchiveRequest,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    """17:30 确认后生成一条工作记录作为当日汇总，并借其存在性锁定计划。"""
    if review_exists(db, device.device_id, body.record_date):
        raise HTTPException(status_code=409, detail="当日计划已归档")
    plans = list(
        db.scalars(
            select(WorkLog).where(
                WorkLog.creator_id == device.device_id,
                WorkLog.record_type == "待办计划",
                WorkLog.record_date == body.record_date,
                WorkLog.data_status == 1,
            )
        ).all()
    )
    lines = [f"{body.record_date.isoformat()} 当日工作汇总"]
    for plan in plans:
        prefix = f"{plan.ext_field_4} " if plan.ext_field_4 else ""
        status_name = PLAN_STATUS_NAMES.get(plan.ext_field_5 if plan.ext_field_5 is not None else 0, "未做")
        lines.append(f"[{status_name}] {prefix}{plan.content}")
        if plan.ext_field_1:
            lines.append(f"  执行说明：{plan.ext_field_1}")
    if body.insight:
        lines.append(f"整体心得：{body.insight.strip()}")
    review = WorkLog(
        record_id=new_id(),
        creator_id=device.device_id,
        data_status=1,
        record_type="每日复盘",
        record_date=body.record_date,
        content="\n".join(lines),
        is_shared=0,
    )
    db.add(review)
    log_operation(
        db,
        device.device_id,
        "add",
        "work",
        review.record_id,
        {"operation": "archive_daily", "record_date": body.record_date.isoformat(), "plan_count": len(plans)},
        request.client.host if request.client else None,
    )
    db.commit()
    db.refresh(review)
    return {
        "review": serialize_record(review, device),
        "plan_count": len(plans),
        "locked": True,
        "plans": [serialize_record(plan, device) for plan in plans],
    }
