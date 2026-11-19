from typing import Literal, Optional

from pydantic import BaseModel, Field


BusinessModule = Literal["sale", "lease", "work", "inspiration"]


class RecordLinkCreate(BaseModel):
    source_module: BusinessModule
    source_record_id: str = Field(min_length=1, max_length=32)
    target_module: BusinessModule
    target_record_id: str = Field(min_length=1, max_length=32)
    relation_type: str = Field(default="related", pattern=r"^(related|evidence|follow_up|same_project)$")
    note: Optional[str] = Field(default=None, max_length=255)
