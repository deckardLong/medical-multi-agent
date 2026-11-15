# product/db/models/reminder_log.py
from uuid import UUID
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class ReminderLog(Base, TimestampMixin):

    __tablename__ = "reminder_logs"
    __table_args__ = (UniqueConstraint("event_id", "occurs_at", name="uq_reminder_event_occurrence"),)

    id: Mapped[UUID] = uuid_pk()
    # CASCADE: xoá lịch thì xoá luôn log nhắc, nếu không DELETE /calendar/{id} lỗi khoá ngoại (500)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    occurs_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)