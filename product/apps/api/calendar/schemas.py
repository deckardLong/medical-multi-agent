from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from product.db.models import EventSource, EventType


class EventIn(BaseModel):
    type: EventType
    title: str = Field(min_length=1, max_length=200)
    starts_at: datetime                       # không kèm múi giờ = giờ địa phương (PRODUCT_TIMEZONE)
    recurrence_rule: str | None = None        # RRULE, vd "FREQ=DAILY;COUNT=7"


class EventOut(BaseModel):
    id: UUID
    type: EventType
    title: str
    starts_at: datetime
    recurrence_rule: str | None
    source: EventSource
    confirmed_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}


class OccurrenceOut(BaseModel):
    """Một lần xảy ra cụ thể của event (lịch lặp 7 ngày = 7 OccurrenceOut cùng event_id)."""
    event_id: UUID
    occurs_at: datetime
    type: EventType
    title: str
    recurrence_rule: str | None
    source: EventSource
    confirmed: bool
