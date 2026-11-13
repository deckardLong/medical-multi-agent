import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_members.id"))
    storage_path: Mapped[str]
    mime_type: Mapped[str]
    extracted_json: Mapped[dict | None] =   mapped_column(JSONB, nullable=True)