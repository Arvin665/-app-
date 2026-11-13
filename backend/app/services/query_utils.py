from datetime import date, datetime, time, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select


def period_bounds(period_type: str, period_value: str) -> tuple[datetime, datetime]:
    """把日/周/月/季/年筛选值统一换算为左闭右开时间区间。"""
    try:
        if period_type == "day":
            start_date = date.fromisoformat(period_value)
            end_date = start_date + timedelta(days=1)
        elif period_type == "week":
            year_str, week_str = period_value.upper().split("-W")
            start_date = date.fromisocalendar(int(year_str), int(week_str), 1)
            end_date = start_date + timedelta(days=7)
        elif period_type == "month":
            year, month = map(int, period_value.split("-"))
            start_date = date(year, month, 1)
            end_date = date(year + (month == 12), month % 12 + 1, 1)
        elif period_type == "quarter":
            year_str, quarter_str = period_value.upper().split("-Q")
            year, quarter = int(year_str), int(quarter_str)
            start_month = (quarter - 1) * 3 + 1
            start_date = date(year, start_month, 1)
            next_month = start_month + 3
            end_date = date(year + (next_month > 12), (next_month - 1) % 12 + 1, 1)
        elif period_type == "year":
            year = int(period_value)
            start_date = date(year, 1, 1)
            end_date = date(year + 1, 1, 1)
        else:
            raise ValueError
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="时间筛选格式不正确") from exc
    return datetime.combine(start_date, time.min), datetime.combine(end_date, time.min)


def apply_period_filter(
    query: Select,
    column: Any,
    period_type: str | None,
    period_value: str | None,
) -> Select:
    if period_type and period_value:
        start_time, end_time = period_bounds(period_type, period_value)
        return query.where(column >= start_time, column < end_time)
    return query
