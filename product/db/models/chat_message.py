import enum
import uuid
from sqlalchemy import Enum as SAEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chat_sessions.id"))
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    # document_id gửi kèm tin nhắn; lưu tách khỏi content để người dùng không thấy dòng ghép thêm cho agent
    attachments: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)