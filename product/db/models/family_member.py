import enum
import uuid
from datetime import date
from sqlalchemy import Date, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class MemberType(str, enum.Enum):
    SELF = "self"
    SPOUSE = "spouse"
    CHILD = "child"
    PARENT = "parent"
    SIBLING = "sibling"
    OTHER_RELATIVE = "other_relative"

class FamilyMember(Base, TimestampMixin):
    __tablename__ = "family_members"

    id = uuid_pk()
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("families.id"))
    member_type: Mapped[MemberType] = mapped_column(SAEnum(MemberType, name="member_type"))
    display_name: Mapped[str]
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Link with person in a family whether they do have / not have their account
    linked_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)