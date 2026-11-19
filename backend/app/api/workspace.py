from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.attachments import serialize_attachment
from app.api.deps import CurrentDevice, DbSession
from app.api.materials import serialize_material_for_device, visible_condition
from app.core.security import new_id
from app.models import (
    Attachment,
    Material,
    PersonalInspiration,
    PropertySale,
    RecordLink,
    TenancyLease,
    WorkLog,
)
from app.schemas.workspace import BusinessModule, RecordLinkCreate
from app.services.record_utils import (
    MODULE_MODELS,
    business_date_of,
    can_read,
    log_operation,
    scope_condition,
    serialize_record,
)

router = APIRouter(prefix="/workspace", tags=["跨模块资料闭环"])

MODULE_LABELS = {
    "sale": "项目买卖",
    "lease": "企业租赁",
    "work": "工作记录",
    "inspiration": "个人灵感",
}
RELATION_LABELS = {
    "related": "相关",
    "evidence": "佐证",
    "follow_up": "跟进",
    "same_project": "同项目",
}
BUSINESS_SEARCH_FIELDS: dict[str, list[tuple[str, str]]] = {
    "sale": [
        ("project_name", "项目"),
        ("district", "区域"),
        ("address", "地址"),
        ("buyer", "买方"),
        ("seller", "卖方"),
        ("remark", "备注"),
    ],
    "lease": [
        ("company_name", "企业"),
        ("new_project", "新项目"),
        ("old_project", "原项目"),
        ("industry", "行业"),
        ("remark", "备注"),
    ],
    "work": [
        ("content", "正文"),
        ("todo_items", "待办"),
        ("related_project", "关联项目"),
        ("tags", "标签"),
    ],
    "inspiration": [("content", "正文"), ("tags", "标签")],
}


def pair_key(module_a: str, record_a: str, module_b: str, record_b: str) -> str:
    left, right = sorted([f"{module_a}:{record_a}", f"{module_b}:{record_b}"])
    return f"{left}|{right}"


def clean_text(value: Optional[str], limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def record_summary(module: str, record: Any) -> dict[str, Any]:
    if module == "sale":
        title = clean_text(record.project_name, 80) or "待补充项目"
        subtitle = " · ".join(
            item
            for item in [
                clean_text(record.district, 30),
                clean_text(record.deal_status, 20),
                f"{record.deal_total_price} 万元" if record.deal_total_price else "",
            ]
            if item
        )
        summary = clean_text(record.remark or record.project_feature, 180)
    elif module == "lease":
        title = clean_text(record.company_name, 80) or "待补充企业"
        subtitle = " · ".join(
            item
            for item in [
                clean_text(record.new_project, 50),
                f"{record.new_area} ㎡" if record.new_area else "",
                clean_text(record.lease_type, 20),
            ]
            if item
        )
        summary = clean_text(record.move_reason or record.company_background or record.remark, 180)
    elif module == "work":
        title = clean_text(record.content, 80) or clean_text(record.record_type, 30) or "工作记录"
        subtitle = " · ".join(
            item
            for item in [
                clean_text(record.record_type, 20),
                clean_text(record.related_project, 50),
                "团队共享" if record.is_shared else "仅本人可见",
            ]
            if item
        )
        summary = clean_text(record.todo_items or record.ext_field_1, 180)
    else:
        title = clean_text(record.content, 80) or "个人灵感"
        subtitle = " · ".join(
            item
            for item in [clean_text(record.inspiration_type, 20), clean_text(record.tags, 60)]
            if item
        )
        summary = clean_text(record.content, 180)

    business_date = business_date_of(record)
    return {
        "module": module,
        "module_label": MODULE_LABELS[module],
        "record_id": record.record_id,
        "title": title,
        "subtitle": subtitle,
        "summary": summary,
        "business_date": business_date.isoformat() if business_date else None,
    }


def get_readable_record(
    db: Session,
    module: str,
    record_id: str,
    device: CurrentDevice,
) -> Any:
    record = db.get(MODULE_MODELS[module], record_id)
    if record is None or not can_read(record, device):
        raise HTTPException(status_code=404, detail="关联记录不存在或无权访问")
    return record


def linked_record_ref(
    link: RecordLink,
    current_module: str,
    current_record_id: str,
    db: Session,
    device: CurrentDevice,
) -> tuple[str, Any] | None:
    if link.source_module == current_module and link.source_record_id == current_record_id:
        module = link.target_module
        record_id = link.target_record_id
    else:
        module = link.source_module
        record_id = link.source_record_id
    record = db.get(MODULE_MODELS[module], record_id)
    if record is None or not can_read(record, device):
        return None
    return module, record


def serialize_link(
    link: RecordLink,
    current_module: str,
    current_record_id: str,
    db: Session,
    device: CurrentDevice,
) -> Optional[dict[str, Any]]:
    resolved = linked_record_ref(link, current_module, current_record_id, db, device)
    if resolved is None:
        return None
    module, record = resolved
    payload = record_summary(module, record)
    payload.update(
        {
            "link_id": link.link_id,
            "relation_type": link.relation_type,
            "relation_label": RELATION_LABELS.get(link.relation_type, "相关"),
            "note": link.note,
            "created_at": link.create_time,
            "can_remove": link.creator_id == device.device_id or device.role_level == 1,
        }
    )
    return payload


def active_links_for(db: Session, module: str, record_id: str) -> list[RecordLink]:
    return list(
        db.scalars(
            select(RecordLink)
            .where(
                RecordLink.data_status == 1,
                or_(
                    and_(
                        RecordLink.source_module == module,
                        RecordLink.source_record_id == record_id,
                    ),
                    and_(
                        RecordLink.target_module == module,
                        RecordLink.target_record_id == record_id,
                    ),
                ),
            )
            .order_by(RecordLink.create_time.desc())
        ).all()
    )


def normalized_name(value: Optional[str]) -> str:
    return "".join(str(value or "").lower().replace("上海市", "").split())


def similar_project(left: Optional[str], right: Optional[str]) -> bool:
    a = normalized_name(left)
    b = normalized_name(right)
    if len(a) < 4 or len(b) < 4:
        return False
    return a in b or b in a


def project_search_terms(values: Iterable[str]) -> list[str]:
    terms: set[str] = set()
    for value in values:
        name = normalized_name(value)
        if len(name) < 4:
            continue
        terms.add(name)
        terms.add(name[:4])
        if len(name) > 6:
            terms.add(name[:6])
    return sorted(terms, key=len, reverse=True)


def suggestion_payload(module: str, record: Any, reason: str) -> dict[str, Any]:
    payload = record_summary(module, record)
    payload.update({"reason": reason, "relation_type": "related", "relation_label": "相关"})
    return payload


def candidate_records(
    db: Session,
    model: type,
    device: CurrentDevice,
    project_names: Iterable[str],
) -> list[Any]:
    names = project_search_terms(project_names)
    if not names:
        return []
    if model is PropertySale:
        match = or_(*[PropertySale.project_name.like(f"%{name}%") for name in names])
        query = select(PropertySale).where(PropertySale.data_status == 1, match)
    elif model is TenancyLease:
        match = or_(
            *[
                or_(
                    TenancyLease.new_project.like(f"%{name}%"),
                    TenancyLease.old_project.like(f"%{name}%"),
                )
                for name in names
            ]
        )
        query = select(TenancyLease).where(TenancyLease.data_status == 1, match)
    elif model is WorkLog:
        match = or_(*[WorkLog.related_project.like(f"%{name}%") for name in names])
        query = select(WorkLog).where(
            WorkLog.data_status == 1,
            scope_condition(WorkLog, device),
            match,
        )
    else:
        return []
    return list(db.scalars(query.order_by(model.update_time.desc()).limit(80)).all())


def build_suggestions(
    db: Session,
    module: str,
    record: Any,
    device: CurrentDevice,
    excluded: set[str],
) -> list[dict[str, Any]]:
    if module in {"sale", "lease"}:
        projects = [
            getattr(record, "project_name", None),
            getattr(record, "new_project", None),
            getattr(record, "old_project", None),
        ]
    elif module == "work":
        projects = [record.related_project]
    else:
        return []

    targets: list[tuple[str, Any, str]] = []
    if module != "sale":
        for candidate in candidate_records(db, PropertySale, device, projects):
            if any(similar_project(project, candidate.project_name) for project in projects if project):
                targets.append(("sale", candidate, f"同楼宇：{candidate.project_name}"))
    if module != "lease":
        for candidate in candidate_records(db, TenancyLease, device, projects):
            candidate_projects = [candidate.new_project, candidate.old_project]
            matched = next(
                (
                    project
                    for project in projects
                    if project
                    and any(similar_project(project, item) for item in candidate_projects if item)
                ),
                None,
            )
            if matched:
                targets.append(("lease", candidate, f"同楼宇：{matched}"))
    if module != "work":
        for candidate in candidate_records(db, WorkLog, device, projects):
            matched = next(
                (
                    project
                    for project in projects
                    if project and similar_project(project, candidate.related_project)
                ),
                None,
            )
            if matched:
                targets.append(("work", candidate, f"工作记录提到：{matched}"))

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for target_module, target, reason in targets:
        if target_module == module and target.record_id == record.record_id:
            continue
        key = pair_key(module, record.record_id, target_module, target.record_id)
        if key in excluded or key in seen:
            continue
        seen.add(key)
        result.append(suggestion_payload(target_module, target, reason))
        if len(result) >= 8:
            break
    return result


def material_search_hit(record: Material) -> dict[str, Any]:
    return {
        "kind": "material",
        "entity_id": record.material_id,
        "module": record.module,
        "module_label": MODULE_LABELS[record.module],
        "record_id": record.record_id,
        "title": record.title,
        "subtitle": f"{record.file_type.upper()} · {record.file_name}",
        "summary": clean_text(record.extracted_text or record.extraction_note, 180),
        "business_date": record.upload_time.isoformat(),
        "file_type": record.file_type,
    }


def attachment_search_hit(record: Attachment) -> dict[str, Any]:
    return {
        "kind": "attachment",
        "entity_id": record.attach_id,
        "module": record.biz_type,
        "module_label": MODULE_LABELS[record.biz_type],
        "record_id": record.biz_id,
        "title": record.file_name,
        "subtitle": f"{record.file_type.upper()} · 早期附件",
        "summary": clean_text(record.ocr_content, 180),
        "business_date": record.upload_time.isoformat(),
        "file_type": record.file_type,
    }


@router.post("/links")
def create_link(
    body: RecordLinkCreate,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    if body.source_module == body.target_module and body.source_record_id == body.target_record_id:
        raise HTTPException(status_code=422, detail="不能把记录关联到自身")
    source = get_readable_record(db, body.source_module, body.source_record_id, device)
    target = get_readable_record(db, body.target_module, body.target_record_id, device)
    key = pair_key(
        body.source_module,
        body.source_record_id,
        body.target_module,
        body.target_record_id,
    )
    existing = db.scalar(select(RecordLink).where(RecordLink.pair_key == key))
    created = existing is None or existing.data_status == 0
    if existing is None:
        existing = RecordLink(
            link_id=new_id(),
            pair_key=key,
            source_module=body.source_module,
            source_record_id=source.record_id,
            target_module=body.target_module,
            target_record_id=target.record_id,
            relation_type=body.relation_type,
            note=clean_text(body.note, 255) or None,
            creator_id=device.device_id,
            data_status=1,
        )
        db.add(existing)
    elif existing.data_status == 0:
        existing.data_status = 1
        existing.relation_type = body.relation_type
        existing.note = clean_text(body.note, 255) or None
        existing.creator_id = device.device_id
    if created:
        log_operation(
            db,
            device.device_id,
            "add",
            body.source_module,
            body.source_record_id,
            {
                "operation": "link_records",
                "link_id": existing.link_id,
                "target_module": body.target_module,
                "target_record_id": body.target_record_id,
            },
            request.client.host if request.client else None,
        )
    db.commit()
    db.refresh(existing)
    payload = serialize_link(existing, body.source_module, body.source_record_id, db, device)
    return {"created": created, "link": payload}


@router.get("/links")
def list_links(
    db: DbSession,
    device: CurrentDevice,
    module: BusinessModule,
    record_id: str,
):
    get_readable_record(db, module, record_id, device)
    items = [
        item
        for link in active_links_for(db, module, record_id)
        if (item := serialize_link(link, module, record_id, db, device)) is not None
    ]
    return {"items": items, "total": len(items)}


@router.delete("/links/{link_id}")
def delete_link(
    link_id: str,
    db: DbSession,
    device: CurrentDevice,
    request: Request,
):
    link = db.scalar(
        select(RecordLink).where(
            RecordLink.link_id == link_id,
            RecordLink.data_status == 1,
        )
    )
    if link is None:
        raise HTTPException(status_code=404, detail="关联不存在")
    get_readable_record(db, link.source_module, link.source_record_id, device)
    get_readable_record(db, link.target_module, link.target_record_id, device)
    if link.creator_id != device.device_id and device.role_level != 1:
        raise HTTPException(status_code=403, detail="只能取消本人创建的关联")
    link.data_status = 0
    log_operation(
        db,
        device.device_id,
        "delete",
        link.source_module,
        link.source_record_id,
        {"operation": "unlink_records", "link_id": link.link_id},
        request.client.host if request.client else None,
    )
    db.commit()
    return {"link_id": link_id, "deleted": True}


@router.get("/records/{module}/{record_id}/context")
def record_context(
    module: BusinessModule,
    record_id: str,
    db: DbSession,
    device: CurrentDevice,
):
    record = get_readable_record(db, module, record_id, device)
    materials = list(
        db.scalars(
            select(Material)
            .where(
                Material.data_status == 1,
                Material.module == module,
                Material.record_id == record_id,
                visible_condition(device),
            )
            .order_by(Material.upload_time.desc())
            .limit(100)
        ).all()
    )
    attachments = list(
        db.scalars(
            select(Attachment)
            .where(
                Attachment.data_status == 1,
                Attachment.biz_type == module,
                Attachment.biz_id == record_id,
            )
            .order_by(Attachment.upload_time.desc())
        ).all()
    )
    links = [
        item
        for link in active_links_for(db, module, record_id)
        if (item := serialize_link(link, module, record_id, db, device)) is not None
    ]
    excluded = {
        pair_key(module, record_id, item["module"], item["record_id"])
        for item in links
    }
    suggestions = build_suggestions(db, module, record, device, excluded)
    return {
        "record": serialize_record(record, device),
        "materials": {
            "items": [serialize_material_for_device(item, device) for item in materials],
            "total": len(materials),
        },
        "attachments": {
            "items": [serialize_attachment(item) for item in attachments],
            "total": len(attachments),
        },
        "links": {"items": links, "total": len(links)},
        "suggestions": {"items": suggestions, "total": len(suggestions)},
    }


@router.get("/search")
def workspace_search(
    db: DbSession,
    device: CurrentDevice,
    keyword: str = Query(..., min_length=1, max_length=100),
    modules: Optional[str] = None,
    kinds: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    module_values = {
        item.strip()
        for item in (modules or ",".join(MODULE_LABELS)).split(",")
        if item.strip()
    }
    if not module_values.issubset(MODULE_LABELS):
        raise HTTPException(status_code=422, detail="modules 包含不支持的模块")
    kind_values = {item.strip() for item in (kinds or "record,material,attachment").split(",") if item.strip()}
    if not kind_values.issubset({"record", "material", "attachment"}):
        raise HTTPException(status_code=422, detail="kinds 包含不支持的资料类型")

    pattern = f"%{keyword.strip()}%"
    hits: list[dict[str, Any]] = []
    models = {
        "sale": PropertySale,
        "lease": TenancyLease,
        "work": WorkLog,
        "inspiration": PersonalInspiration,
    }
    for module in module_values:
        model = models[module]
        fields = BUSINESS_SEARCH_FIELDS[module]
        conditions = [getattr(model, key).like(pattern) for key, _ in fields]
        query = select(model).where(model.data_status == 1, or_(*conditions))
        if module in {"work", "inspiration"}:
            query = query.where(scope_condition(model, device))
        records = list(db.scalars(query.order_by(model.update_time.desc()).limit(160)).all())
        if "record" in kind_values:
            for record in records:
                hit = record_summary(module, record)
                hit.update(
                    {
                        "kind": "record",
                        "entity_id": record.record_id,
                        "matched_fields": [
                            label
                            for key, label in fields
                            if keyword.strip().lower() in str(getattr(record, key, "") or "").lower()
                        ],
                    }
                )
                hits.append(hit)

    if "material" in kind_values:
        material_query = select(Material).where(
            Material.data_status == 1,
            visible_condition(device),
            Material.module.in_(module_values),
            or_(
                Material.title.like(pattern),
                Material.file_name.like(pattern),
                Material.extracted_text.like(pattern),
            ),
        )
        for record in db.scalars(material_query.order_by(Material.upload_time.desc()).limit(240)).all():
            hits.append(material_search_hit(record))

    if "attachment" in kind_values:
        attachment_query = select(Attachment).where(
            Attachment.data_status == 1,
            Attachment.biz_type.in_(module_values),
            or_(Attachment.file_name.like(pattern), Attachment.ocr_content.like(pattern)),
        )
        attachment_hits: list[Attachment] = []
        for record in db.scalars(attachment_query.order_by(Attachment.upload_time.desc()).limit(160)).all():
            parent = db.get(MODULE_MODELS[record.biz_type], record.biz_id)
            if parent is not None and can_read(parent, device):
                attachment_hits.append(record)
        hits.extend(attachment_search_hit(record) for record in attachment_hits)

    def sort_key(item: dict[str, Any]):
        query_text = keyword.strip().lower()
        title_match = query_text in str(item.get("title") or "").lower()
        date_value = str(item.get("business_date") or "")
        try:
            timestamp = datetime.fromisoformat(date_value).timestamp()
        except (ValueError, TypeError):
            timestamp = 0.0
        return (not title_match, -timestamp)

    hits.sort(key=sort_key)
    total = len(hits)
    start = (page - 1) * page_size
    return {
        "items": hits[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "keyword": keyword.strip(),
        "modules": sorted(module_values),
    }
