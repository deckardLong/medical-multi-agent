import uuid
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"

    id = uuid_pk()
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("family_members.id"))