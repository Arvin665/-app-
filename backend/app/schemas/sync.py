from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SyncRecord(BaseModel):
    record_id: str = Field(min_length=32, max_length=32)
    client_updated_at: datetime
    data: dict[str, Any]


class SyncPushRequest(BaseModel):
    module: str
    records: list[SyncRecord]


class SyncPushResponse(BaseModel):
    module: str
    accepted: list[str]
    skipped: list[str]
    conflicts: list[str]
    server_time: datetime


class SyncPullResponse(BaseModel):
    module: str
    records: list[dict[str, Any]]
    server_time: datetime
