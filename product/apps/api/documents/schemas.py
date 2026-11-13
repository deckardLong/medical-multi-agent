from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: UUID
    mime_type: str
    created_at: datetime
    extracted_json: dict | None = None
    model_config = {"from_attributes": True}
