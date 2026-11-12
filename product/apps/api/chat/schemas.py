from uuid import UUID
from pydantic import BaseModel
from product.db.models import MessageRole

class SendMessageIn(BaseModel):
    content: str

class ChatMessageOut(BaseModel):
    id: UUID
    role: MessageRole
    content: str
    model_config = {"from_attributes": True}