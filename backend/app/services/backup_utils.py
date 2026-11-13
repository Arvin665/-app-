from datetime import date, datetime
from decimal import Decimal
from typing import Any


def model_to_dict(row: Any, decrypt_sensitive: bool = False) -> dict[str, Any]:
    """把 ORM 行转换为可 JSON 化字典，日期保留 ISO 字符串。"""
    result: dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, (date, datetime)):
            value = value.isoformat()
        elif isinstance(value, Decimal):
            value = str(value)
        result[column.name] = value
    if decrypt_sensitive and hasattr(row, "decrypted_commission_remark"):
        result["commission_remark"] = row.decrypted_commission_remark
    return result
