from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from product.db.models import RecordKind


class StatusFilter(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    ALL = "all"


class RecordIn(BaseModel):
    kind: RecordKind
    payload: dict[str, Any] = Field(min_length=1)


class RecordConfirmIn(BaseModel):
    payload: dict[str, Any] | None = Field(default=None, min_length=1)   # bản đã sửa; bỏ trống = giữ nguyên đề xuất


class RecordOut(BaseModel):
    id: UUID
    kind: RecordKind
    payload: dict[str, Any]
    source_document_id: UUID | None
    confirmed_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}
