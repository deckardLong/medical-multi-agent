import enum
from datetime import date
from sqlalchemy import Date, Enum as SAEnum
from sqlalchemy import false
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, TimestampMixin, uuid_pk

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = uuid_pk()
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password_hash: Mapped[str]  = mapped_column(nullable=True)
    display_name: Mapped[str]
    email_verified: Mapped[bool] = mapped_column(server_default=false())
    # Nullable để tài khoản tạo trước khi có các trường này vẫn hợp lệ
    last_name: Mapped[str | None] = mapped_column(nullable=True)        # Họ (kèm tên đệm)
    first_name: Mapped[str | None] = mapped_column(nullable=True)       # Tên
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(SAEnum(Gender, name="gender"), nullable=True)
    phone: Mapped[str | None] = mapped_column(nullable=True)
