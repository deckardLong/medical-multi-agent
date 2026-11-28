import enum
import uuid
from sqlalchemy import Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class OAuthProvider(str, enum.Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"

class OAuthAccount(Base, TimestampMixin):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_oauth_provider_subject"),  # 1 tài khoản Google chỉ gắn 1 user
        UniqueConstraint("user_id", "provider", name="uq_oauth_user_provider"),     # 1 user chỉ gắn 1 tài khoản Google
    )

    id = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[OAuthProvider] = mapped_column(SAEnum(OAuthProvider, name="oauth_provider"))
    subject: Mapped[str]
    email: Mapped[str | None] = mapped_column(nullable=True)