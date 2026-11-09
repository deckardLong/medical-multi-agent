import enum
import uuid
from sqlalchemy import Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class ConnectionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"

class Connection(Base, TimestampMixin):
    __tablename__ = "connections"
    __table_args__ = (UniqueConstraint("requester_user_id", "target_user_id", name="uq_connection_pair"),)

    id = uuid_pk()
    requester_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    target_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[ConnectionStatus] = mapped_column(SAEnum(ConnectionStatus, name="connection_status"), default=ConnectionStatus.PENDING)