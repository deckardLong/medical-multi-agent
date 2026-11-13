from uuid import UUID
from pydantic import BaseModel
from product.db.models import MessageRole

class SendMessageIn(BaseModel):
    content: str
    document_ids: list[UUID] = []   # id trả về từ POST /members/{member_id}/documents

class ChatMessageOut(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    attachments: list[UUID] | None = None
    model_config = {"from_attributes": True}