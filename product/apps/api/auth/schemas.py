from datetime import date
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from product.db.models import Gender

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    last_name: str | None = Field(default=None, max_length=60)      # Họ (kèm tên đệm)
    first_name: str | None = Field(default=None, max_length=40)     # Tên
    display_name: str | None = Field(default=None, max_length=100)  # bỏ trống = "Họ Tên"
    date_of_birth: date | None = None
    gender: Gender | None = None
    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 .-]{8,20}$")

    @field_validator("last_name", "first_name", "display_name", "phone", mode="before")
    @classmethod
    def _strip(cls, v):
        return (v.strip() or None) if isinstance(v, str) else v

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v: date | None):
        if v is not None and not (date(1900, 1, 1) <= v <= date.today()):
            raise ValueError("Ngày sinh không hợp lệ")
        return v

    @model_validator(mode="after")
    def _fill_display_name(self):
        if not self.display_name:
            self.display_name = " ".join(p for p in (self.last_name, self.first_name) if p) or None
        if not self.display_name:
            raise ValueError("Cần nhập họ tên (hoặc display_name)")
        return self

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    last_name: str | None = None
    first_name: str | None = None
    date_of_birth: date | None = None
    gender: Gender | None = None
    phone: str | None = None

    model_config = {
        "from_attributes": True
    }
