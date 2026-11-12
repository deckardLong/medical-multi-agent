from datetime import date
from uuid import UUID
from pydantic import BaseModel, EmailStr
from product.db.models import MemberType, ConnectionStatus

class FamilyOut(BaseModel):
    id: UUID
    name: str
    model_config = {"from_attributes": True}

class FamilyMemberIn(BaseModel):
    display_name: str
    member_type: MemberType
    dob: date | None = None

class FamilyMemberOut(BaseModel):
    id: UUID
    family_id: UUID
    member_type: MemberType
    display_name: str
    dob: date | None 
    linked_user_id: UUID | None
    model_config = {"from_attributes": True}

class ConnectionRequestIn(BaseModel):
    target_email: EmailStr

class ConnectionOut(BaseModel):
    id: UUID
    requester_user_id: UUID
    target_user_id: UUID
    status: ConnectionStatus
    model_config = {"from_attributes": True}

class AttachConnectionIn(BaseModel):
    connection_id: UUID
    member_type: MemberType