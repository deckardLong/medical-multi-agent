import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class RecordKind(str, enum.Enum):
    CONDITION = "condition"
    MEDICATION = "medication"
    ALLERGY = "allergy"
    LAB_RESULT = "lab_result"

class MedicalRecord(Base, TimestampMixin):
    __tablename__ = "medical_records"

    id = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_members.id"))
    kind: Mapped[RecordKind] = mapped_column(SAEnum(RecordKind, name="record_kind"))
    payload: Mapped[dict] = mapped_column(JSONB)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    # Wait for user confirm
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)