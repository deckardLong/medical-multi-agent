# product/apps/api/dashboard/schemas.py
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel
from product.db.models import EventType, MemberType

class Summary(BaseModel):
    consultations_this_month: int
    documents_total: int
    upcoming_7d: int
    pending_confirmations: int          # đề xuất hồ sơ + lịch chưa xác nhận

class MemberCard(BaseModel):
    id: UUID
    display_name: str
    member_type: MemberType
    age: int | None
    avatar_updated_at: datetime | None = None   # có giá trị = có ảnh đại diện; dùng làm ?v= khi tải ảnh
    health_visible: bool                 # False: thành viên tự quản lý hồ sơ, chủ gia đình không xem được
    # null khi health_visible=False: [] sẽ bị đọc thành "không có dị ứng" trong khi thực ra là "không được xem"
    confirmed_records: int | None = None
    allergies: list[str] | None = None
    conditions: list[str] | None = None

class TimelineItem(BaseModel):
    at: datetime
    member_id: UUID
    member_name: str
    kind: Literal["document_uploaded", "record_confirmed"]
    label: str

class UpcomingItem(BaseModel):
    at: datetime
    member_id: UUID
    member_name: str
    title: str
    type: EventType

class DashboardOut(BaseModel):
    summary: Summary
    members: list[MemberCard]
    timeline: list[TimelineItem]
    upcoming: list[UpcomingItem]