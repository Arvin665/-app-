from typing import Any, Optional

from pydantic import BaseModel, Field


class AIExtractResponse(BaseModel):
    module: str
    fields: dict[str, Any]
    confidence: dict[str, float]
    missing_fields: list[str]
    provider: str
    note: str


class CommandRequest(BaseModel):
    module: str
    current_fields: dict[str, Any]
    command: str = Field(min_length=1)


class CommandResponse(BaseModel):
    module: str
    fields: dict[str, Any]
    changed_fields: list[str]
    confidence: dict[str, float]
    note: Optional[str] = None
