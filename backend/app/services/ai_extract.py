import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from app.core.config import settings

MODULE_REQUIRED_FIELDS = {
    "sale": ["project_name", "district", "deal_date", "deal_total_price", "buyer"],
    "lease": ["company_name", "new_project", "lease_type", "start_date", "new_area"],
    "work": ["record_date", "content"],
    "inspiration": ["record_time", "content"],
}

FIELD_LABELS = {
    "sale": {
        "项目名": "project_name",
        "项目名称": "project_name",
        "区域": "district",
        "地址": "address",
        "总价": "deal_total_price",
        "交易总价": "deal_total_price",
        "单价": "deal_unit_price",
        "卖家": "seller",
        "原业主": "seller",
        "买家": "buyer",
        "受让方": "buyer",
        "交易方式": "deal_type",
        "主居间": "main_intermediary",
        "佣金备注": "commission_remark",
        "备注": "remark",
    },
    "lease": {
        "企业名": "company_name",
        "企业名称": "company_name",
        "行业": "industry",
        "原办公项目": "old_project",
        "新办公项目": "new_project",
        "新项目": "new_project",
        "面积": "new_area",
        "租赁类型": "lease_type",
        "租金": "rent_price",
        "起租日期": "start_date",
        "主居间": "main_intermediary",
        "备注": "remark",
    },
    "work": {
        "记录日期": "record_date",
        "计划时间": "ext_field_4",
        "计划执行时分": "ext_field_4",
        "记录类型": "record_type",
        "内容": "content",
        "计划内容": "content",
        "关联项目": "related_project",
    },
    "inspiration": {"灵感类型": "inspiration_type", "内容": "content", "记录时间": "record_time"},
}

DISTRICTS = [
    "浦东",
    "黄浦",
    "徐汇",
    "长宁",
    "静安",
    "普陀",
    "虹口",
    "杨浦",
    "闵行",
    "宝山",
    "嘉定",
    "金山",
    "松江",
    "青浦",
    "奉贤",
    "崇明",
]


def parse_date(text: str, field: str = "date") -> tuple[Optional[str], float]:
    """支持 ISO、中文年月日和“今天/明天”等常用录入表达。"""
    today = date.today()
    if "明天" in text:
        return (today.fromordinal(today.toordinal() + 1).isoformat(), 0.98)
    if "今天" in text or "今日" in text:
        return (today.isoformat(), 0.98)
    full = re.search(r"(20\d{2})[年/-](\d{1,2})[月/-](\d{1,2})日?", text)
    if full:
        try:
            return date(int(full.group(1)), int(full.group(2)), int(full.group(3))).isoformat(), 0.98
        except ValueError:
            pass
    short = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if short:
        try:
            return date(today.year, int(short.group(1)), int(short.group(2))).isoformat(), 0.9
        except ValueError:
            pass
    iso = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1), 0.99
    if field == "record_time":
        return datetime.now().isoformat(timespec="seconds"), 0.55
    return None, 0.0


def parse_money_wan(text: str, labels: list[str]) -> tuple[Optional[str], float]:
    """把亿元换算为万元，保证字段单位与数据库定义一致。"""
    for label in labels:
        pattern = rf"{label}[^0-9]{{0,6}}(\d+(?:\.\d+)?)\s*(亿|万)?"
        match = re.search(pattern, text)
        if not match:
            continue
        value = Decimal(match.group(1))
        unit = match.group(2)
        if unit == "亿":
            value *= 10000
        elif not unit and value < 100:
            # 总价“3.2”在商办语境下通常为亿元，规则模拟给出较低置信度提示核对。
            value *= 10000
            return str(value.quantize(Decimal("0.01"))), 0.62
        return str(value.quantize(Decimal("0.01"))), 0.92
    return None, 0.0


def extract_text(text: str, module: str) -> dict[str, Any]:
    """本地规则模拟 NLP 提取，不调用任何外部模型，结果需用户核对。"""
    normalized = re.sub(r"\s+", " ", text or "").strip()
    fields: dict[str, Any] = {}
    confidence: dict[str, float] = {}

    if module == "sale":
        project = re.search(r"(?:项目名称|项目名|项目)[：:是为]?\s*([^，。；,;\s]{2,40})", normalized)
        if project:
            fields["project_name"] = project.group(1)
            confidence["project_name"] = 0.9
        for district in DISTRICTS:
            if district in normalized:
                tail = re.search(rf"{district}(?:[-－]([^，。；,;\s]+))?", normalized)
                fields["district"] = district + (f"-{tail.group(1)}" if tail and tail.group(1) else "")
                confidence["district"] = 0.88
                break
        deal_date, date_conf = parse_date(normalized)
        if deal_date:
            fields["deal_date"] = deal_date
            confidence["deal_date"] = date_conf
        total_price, total_conf = parse_money_wan(normalized, ["交易总价", "成交总价", "总价", "成交价"])
        if total_price:
            fields["deal_total_price"] = total_price
            confidence["deal_total_price"] = total_conf
        for label, key, conf in [
            (r"(?:买家|受让方)[：:是为]?\s*([^，。；,;\s]{2,50})", "buyer", 0.9),
            (r"(?:卖家|原业主方?)[：:是为]?\s*([^，。；,;\s]{2,50})", "seller", 0.86),
            (r"(?:主居间方?)[：:是为]?\s*([^，。；,;\s]{2,50})", "main_intermediary", 0.82),
        ]:
            match = re.search(label, normalized)
            if match:
                fields[key] = match.group(1)
                confidence[key] = conf

    elif module == "lease":
        company = re.search(r"(?:企业名称|企业名|公司名)[：:是为]?\s*([^，。；,;\s]{2,50})", normalized)
        if company:
            fields["company_name"] = company.group(1)
            confidence["company_name"] = 0.9
        new_project = re.search(r"(?:新办公项目|新项目|搬到|迁至)[：:是为]?\s*([^，。；,;\s]{2,50})", normalized)
        if new_project:
            fields["new_project"] = new_project.group(1)
            confidence["new_project"] = 0.88
        area = re.search(r"(?:面积|租赁面积)[^0-9]{0,6}(\d+(?:\.\d+)?)\s*(?:平方米|平米|㎡|m2)?", normalized)
        if area:
            fields["new_area"] = area.group(1)
            confidence["new_area"] = 0.86
        rent = re.search(r"(?:租金|单价)[^0-9]{0,6}(\d+(?:\.\d+)?)", normalized)
        if rent:
            fields["rent_price"] = rent.group(1)
            confidence["rent_price"] = 0.78
        for value in ["新租", "续租", "扩租", "搬迁"]:
            if value in normalized:
                fields["lease_type"] = value
                confidence["lease_type"] = 0.82
                break
        start_date, date_conf = parse_date(normalized)
        if start_date:
            fields["start_date"] = start_date
            confidence["start_date"] = date_conf
        industry = re.search(r"(?:所属行业|行业)[：:是为]?\s*([^，。；,;\s]{2,30})", normalized)
        if industry:
            fields["industry"] = industry.group(1)
            confidence["industry"] = 0.84

    elif module == "work":
        record_date, date_conf = parse_date(normalized, "record_date")
        fields["record_date"] = record_date or date.today().isoformat()
        confidence["record_date"] = date_conf or 0.55
        time_match = re.search(r"(?<!\d)([01]?\d|2[0-3])[:：]([0-5]\d)", normalized)
        # “明天10点”是移动端最常用的计划表达，不能只识别 10:00。
        if not time_match:
            time_match = re.search(r"(?<!\d)([01]?\d|2[0-3])点(半|[0-5]?\d分?)?", normalized)
        if time_match:
            minute = time_match.group(2) or "00"
            minute = "30" if minute == "半" else minute.replace("分", "").zfill(2)
            fields["ext_field_4"] = f"{int(time_match.group(1)):02d}:{minute}"
            confidence["ext_field_4"] = 0.92
        cleaned = re.sub(r"(?:20\d{2}年)?\d{1,2}月\d{1,2}日|今天|明天|上午|下午|晚上", "", normalized).strip()
        cleaned = re.sub(r"(?<!\d)([01]?\d|2[0-3])(?:[:：][0-5]\d|点(?:半|[0-5]?\d分?)?)", "", cleaned).strip()
        fields["content"] = cleaned or normalized
        confidence["content"] = 0.75
        # 明确时间点通常代表待办计划，避免用户额外选择一次记录类型。
        fields["record_type"] = "待办计划" if ("计划" in normalized or "提醒" in normalized or time_match) else "每日心得"

    elif module == "inspiration":
        fields["content"] = normalized
        confidence["content"] = 0.9
        fields["record_time"] = datetime.now().isoformat(timespec="seconds")
        confidence["record_time"] = 0.55
        for item in ["想法", "灵感", "行业观察", "人脉", "业务线索"]:
            if item in normalized:
                fields["inspiration_type"] = item
                confidence["inspiration_type"] = 0.7
                break

    else:
        raise ValueError("module 必须是 sale/lease/work/inspiration")

    return {"fields": fields, "confidence": confidence}


def extract_response(text: str, module: str, provider_note: str = "") -> dict[str, Any]:
    result = extract_text(text, module)
    fields = result["fields"]
    missing = [field for field in MODULE_REQUIRED_FIELDS[module] if fields.get(field) in (None, "")]
    note = "当前使用本地规则模拟实现，未调用第三方 OCR/ASR/NLP；所有结果均需人工核对。"
    if provider_note:
        note = f"{note} {provider_note}"
    return {
        "module": module,
        "fields": fields,
        "confidence": result["confidence"],
        "missing_fields": missing,
        "provider": settings.ai_provider,
        "note": note,
    }


def apply_command(module: str, current_fields: dict[str, Any], command: str) -> dict[str, Any]:
    """自然语言修正：只更新命令中明确提到的字段，其余字段保持原值。"""
    if module not in FIELD_LABELS:
        raise ValueError("不支持的业务模块")
    updated = dict(current_fields)
    changed: list[str] = []
    confidence: dict[str, float] = {}
    labels = sorted(FIELD_LABELS[module].items(), key=lambda item: len(item[0]), reverse=True)

    for label, field in labels:
        if label not in command:
            continue
        value_match = re.search(rf"{re.escape(label)}\s*(?:改成|改为|调整为|更新为|是|为|：|:)\s*([^，。；,;]+)", command)
        if not value_match:
            continue
        raw_value = value_match.group(1).strip()
        if field in {"deal_total_price", "deal_unit_price"}:
            parsed, conf = parse_money_wan(f"{label} {raw_value}", [label])
            if parsed is None:
                continue
            value = parsed
        elif field in {"deal_date", "start_date", "record_date", "record_time"}:
            value, conf = parse_date(raw_value, field)
        elif field in {"new_area", "rent_price", "property_fee"}:
            number = re.search(r"\d+(?:\.\d+)?", raw_value)
            if not number:
                continue
            value, conf = number.group(0), 0.82
        else:
            value = raw_value.strip(' "')
            conf = 0.92
        if value is not None and value != "":
            updated[field] = value
            changed.append(field)
            confidence[field] = conf

    # 命令没有使用“字段名+值”句式时，尝试把整句作为对应模块文本内容。
    if not changed and module in {"work", "inspiration"}:
        extracted = extract_text(command, module)
        for field in ["content", "ext_field_4", "record_date"]:
            if field in extracted["fields"]:
                updated[field] = extracted["fields"][field]
                changed.append(field)
                confidence[field] = extracted["confidence"].get(field, 0.7)

    return {
        "module": module,
        "fields": updated,
        "changed_fields": sorted(set(changed)),
        "confidence": confidence,
        "note": "本地规则已完成修正解析，请核对后保存。" if changed else "未识别到可更新字段，请使用“字段名+值”的表达。",
    }
