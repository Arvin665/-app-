import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from app.core.config import settings

MODULE_REQUIRED_FIELDS = {
    "sale": [],
    "lease": ["company_name", "new_project", "lease_type", "start_date", "new_area"],
    "work": ["record_date", "content"],
    "inspiration": ["record_time", "content"],
}

FIELD_LABELS = {
    "sale": {
        "项目名称": "project_name",
        "项目名": "project_name",
        "项目": "project_name",
        "所在区域": "district",
        "区域": "district",
        "详细地址": "address",
        "地址": "address",
        "交易总价": "deal_total_price",
        "成交总价": "deal_total_price",
        "成交价": "deal_total_price",
        "总价": "deal_total_price",
        "成交单价": "deal_unit_price",
        "单价": "deal_unit_price",
        "原业主方": "seller",
        "原业主": "seller",
        "出售方": "seller",
        "卖家": "seller",
        "受让方": "buyer",
        "买家": "buyer",
        "交易时间": "deal_date",
        "成交日期": "deal_date",
        "交易日期": "deal_date",
        "交易方式": "deal_type",
        "交易标的": "deal_target",
        "交易状态": "deal_status",
        "总建筑面积": "total_area",
        "总面积": "total_area",
        "标准层面积": "standard_floor_area",
        "总楼层": "total_floors",
        "物业等级": "property_grade",
        "项目核心特点": "project_feature",
        "核心特点": "project_feature",
        "买家用途": "buyer_purpose",
        "购置用途": "buyer_purpose",
        "是否有居间": "has_intermediary",
        "主居间方": "main_intermediary",
        "主居间": "main_intermediary",
        "联合居间方": "joint_intermediary",
        "佣金备注": "commission_remark",
        "交易背景": "deal_background",
        "内部趣事": "inside_story",
        "传闻": "inside_story",
        "标签": "tags",
        "备注": "remark",
    },
    "lease": {
        "企业名称": "company_name",
        "企业名": "company_name",
        "公司名": "company_name",
        "新办公项目": "new_project",
        "新项目": "new_project",
        "租赁类型": "lease_type",
        "起租日期": "start_date",
        "新租赁面积": "new_area",
        "租赁面积": "new_area",
        "面积": "new_area",
        "所属行业": "industry",
        "行业": "industry",
        "企业规模": "company_scale",
        "原办公项目": "old_project",
        "原租赁面积": "old_area",
        "原租约到期时间": "old_expire_date",
        "所在楼层": "floor",
        "租金单价": "rent_price",
        "租金": "rent_price",
        "物业费标准": "property_fee",
        "物业费": "property_fee",
        "免租期": "rent_free_period",
        "签约年限": "lease_term",
        "到期日期": "end_date",
        "租金递增": "rent_increase",
        "主居间方": "main_intermediary",
        "主居间": "main_intermediary",
        "联合居间方": "joint_intermediary",
        "经办经纪人": "broker_name",
        "搬迁原因": "move_reason",
        "企业动态背景": "company_background",
        "标签": "tags",
        "备注": "remark",
    },
    "work": {
        "记录类型": "record_type",
        "记录日期": "record_date",
        "计划执行时分": "ext_field_4",
        "计划时间": "ext_field_4",
        "记录正文": "content",
        "计划内容": "content",
        "内容": "content",
        "关联项目": "related_project",
        "跟进状态": "follow_status",
        "团队共享": "is_shared",
        "完成说明": "ext_field_1",
        "待办事项": "todo_items",
        "标签": "tags",
    },
    "inspiration": {
        "灵感类型": "inspiration_type",
        "记录时间": "record_time",
        "灵感正文": "content",
        "内容": "content",
        "自定义标签": "tags",
        "标签": "tags",
        "扩展备注": "ext_field_1",
    },
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

DATE_FIELDS = {"deal_date", "start_date", "old_expire_date", "end_date", "record_date"}
NUMBER_FIELDS = {
    "deal_total_price",
    "deal_unit_price",
    "total_area",
    "standard_floor_area",
    "new_area",
    "old_area",
    "rent_price",
    "property_fee",
    "rent_free_period",
    "lease_term",
}
SWITCH_FIELDS = {"is_shared"}
FIELD_OPTIONS = {
    "deal_type": ["买卖", "股权交易", "资产转让", "司法拍卖", "其他"],
    "deal_status": ["信息待补充", "洽谈中", "意向中", "已签约", "已成交", "已终止"],
    "has_intermediary": ["是", "否"],
    "lease_type": ["新租", "续租", "扩租", "搬迁"],
    "record_type": [
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
    ],
    "inspiration_type": ["想法", "灵感", "行业观察", "人脉", "业务线索"],
}

CHINESE_DIGITS = {"零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def chinese_number(token: str) -> int | None:
    token = token.strip()
    if token.isdigit():
        return int(token)
    if not token or any(char not in CHINESE_DIGITS and char != "十" for char in token):
        return None
    if "十" not in token:
        return CHINESE_DIGITS.get(token) if len(token) == 1 else None
    left, _, right = token.partition("十")
    tens = CHINESE_DIGITS.get(left, 1) if left else 1
    ones = CHINESE_DIGITS.get(right, 0) if right else 0
    return tens * 10 + ones


def parse_time(text: str) -> tuple[Optional[str], float]:
    if "现在" in text or "刚刚" in text:
        return datetime.now().strftime("%H:%M"), 0.85
    colon = re.search(r"(?<!\d)([01]?\d|2[0-3])[:：]([0-5]\d)", text)
    if colon:
        return f"{int(colon.group(1)):02d}:{colon.group(2)}", 0.96
    spoken = re.search(r"(?<!\d)([0-9一二两三四五六七八九十]{1,3})\s*点\s*([0-5]?\d|[一二三四五六七八九十]{1,3})?\s*(半|分)?", text)
    if not spoken:
        return None, 0.0
    hour = chinese_number(spoken.group(1))
    if hour is None or hour > 23:
        return None, 0.0
    minute_token = spoken.group(2)
    if spoken.group(3) == "半":
        minute = 30
    else:
        minute = chinese_number(minute_token) if minute_token else 0
    if minute is None or minute > 59:
        minute = 0
    if any(token in text for token in ("下午", "晚上", "傍晚")) and hour < 12:
        hour += 12
    if "中午" in text and hour < 11:
        hour += 12
    return f"{hour:02d}:{minute:02d}", 0.9


def parse_number(text: str) -> tuple[Optional[str], float]:
    match = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    if not match:
        return None, 0.0
    return match.group(1), 0.92


def parse_date(text: str, field: str = "date") -> tuple[Optional[str], float]:
    """支持 ISO、中文年月日和“今天/明天”等常用录入表达。"""
    today = date.today()
    relative_days = (("大后天", 3), ("后天", 2), ("明天", 1), ("今天", 0), ("今日", 0))
    for token, offset in relative_days:
        if token in text:
            return (today.fromordinal(today.toordinal() + offset).isoformat(), 0.98)
    weekday_match = re.search(r"(下)?(?:周|星期)([一二三四五六日天])", text)
    if weekday_match:
        target = "一二三四五六日".index("日" if weekday_match.group(2) == "天" else weekday_match.group(2))
        current = today.weekday()
        offset = (target - current) % 7
        if offset == 0:
            offset = 7
        return (today.fromordinal(today.toordinal() + offset).isoformat(), 0.9)
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


def _strip_field_prefix(module: str, field: str, text: str) -> str:
    cleaned = text.strip().strip("，。；,;。 ")
    aliases = [label for label, mapped in FIELD_LABELS[module].items() if mapped == field]
    aliases.sort(key=len, reverse=True)
    for label in aliases:
        cleaned = re.sub(rf"^{re.escape(label)}\s*(?:改成|改为|调整为|更新为|是|为|：|:)?\s*", "", cleaned)
    return cleaned.strip()


def parse_field_value(module: str, field: str, text: str) -> dict[str, Any]:
    """把单字段语音转写解析成可写入值；不依赖“字段名+值”固定句式。"""
    if module not in FIELD_LABELS:
        raise ValueError("不支持的业务模块")
    if field not in set(FIELD_LABELS[module].values()):
        raise ValueError("该字段不属于当前模块")
    cleaned = _strip_field_prefix(module, field, text or "")
    value: Any = None
    confidence = 0.0
    note = "已从语音中解析，请核对后保存。"
    if not cleaned:
        return {"module": module, "field": field, "value": None, "confidence": 0.0, "note": "没有识别到可写入内容。"}

    if field in DATE_FIELDS:
        value, confidence = parse_date(cleaned)
    elif field == "record_time":
        parsed_date, date_confidence = parse_date(cleaned)
        parsed_time, time_confidence = parse_time(cleaned)
        chosen_date = parsed_date or date.today().isoformat()
        chosen_time = parsed_time or datetime.now().strftime("%H:%M")
        value = f"{chosen_date}T{chosen_time}:00"
        confidence = max(date_confidence, time_confidence, 0.76)
    elif field == "ext_field_4":
        value, confidence = parse_time(cleaned)
    elif field in NUMBER_FIELDS:
        if field == "deal_total_price":
            match = re.search(r"(\d+(?:\.\d+)?)\s*(亿|万)?", cleaned.replace(",", ""))
            if match:
                amount = Decimal(match.group(1))
                unit = match.group(2)
                if unit == "亿":
                    amount *= 10000
                    confidence = 0.96
                elif unit == "万":
                    confidence = 0.94
                elif amount < 100:
                    amount *= 10000
                    confidence = 0.64
                else:
                    confidence = 0.88
                value = str(amount.quantize(Decimal("0.01")))
        else:
            value, confidence = parse_number(cleaned)
    elif field in SWITCH_FIELDS:
        if re.search(r"不共享|不公开|否|仅本人|私有", cleaned):
            value, confidence = 0, 0.94
        elif re.search(r"共享|公开|是|团队", cleaned):
            value, confidence = 1, 0.94
    elif field in FIELD_OPTIONS:
        aliases = {
            "签约": "已签约",
            "成交": "已成交",
            "洽谈": "洽谈中",
            "意向": "意向中",
            "终止": "已终止",
            "待核实": "信息待补充",
            "待补充": "信息待补充",
            "复盘": "每日复盘",
            "待办": "待办计划",
        }
        for option in FIELD_OPTIONS[field]:
            if option in cleaned:
                value, confidence = option, 0.96
                break
        if value is None:
            for alias, option in aliases.items():
                if alias in cleaned and option in FIELD_OPTIONS[field]:
                    value, confidence = option, 0.88
                    break
    elif field == "district":
        for district in DISTRICTS:
            if district in cleaned:
                tail = re.search(rf"{district}(?:[-－]([^，。；,;\s]+))?", cleaned)
                value = district + (f"-{tail.group(1)}" if tail and tail.group(1) else "")
                confidence = 0.92
                break
    elif field == "tags":
        value = re.sub(r"[、，;；\s]+", ",", cleaned).strip(",")
        confidence = 0.9 if value else 0.0
    else:
        value = re.sub(r"^(?:改成|改为|调整为|更新为|是|为)\s*", "", cleaned).strip()
        confidence = 0.9 if value else 0.0

    if value in (None, ""):
        note = "没有识别到适合该字段的值，请换一种说法重试。"
    return {
        "module": module,
        "field": field,
        "value": value,
        "confidence": round(float(confidence), 2),
        "note": note,
    }


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
    note = "正文识别使用本地 OCR/ASR，字段结构化使用本地规则；所有结果均需人工核对。"
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
        parsed = parse_field_value(module, field, raw_value)
        value = parsed["value"]
        conf = parsed["confidence"]
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
