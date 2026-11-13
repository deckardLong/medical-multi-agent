import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class EventType(str, enum.Enum):
    APPOINTMENT = "appointment"
    MEDICATION_REMINDER = "medication_reminder"
    FOLLOW_UP = "follow_up"

class EventSource(str, enum.Enum):
    MANUAL = "manual"
    AGENT = "agent"

class CalendarEvent(Base, TimestampMixin):
    __tablename__ = "calendar_events"

    id = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_members.id"))
    type: Mapped[EventType] = mapped_column(SAEnum(EventType, name="event_type"))
    title: Mapped[str]
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recurrence_rule: Mapped[str | None] = mapped_column(nullable=True)          # RRULE, vd "FREQ=DAILY;COUNT=7"
    source: Mapped[EventSource] = mapped_column(SAEnum(EventSource, name="event_source"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)