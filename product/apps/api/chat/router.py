from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import FamilyMember
from product.db.session import get_session
from product.apps.api.members.deps import readable_member, writable_member
from . import service
from .schemas import SendMessageIn, ChatMessageOut

router = APIRouter(prefix="/members/{member_id}/chat", tags=["chat"])

@router.post("", response_model=ChatMessageOut)
async def send(data: SendMessageIn, member: FamilyMember = Depends(writable_member),
               session: AsyncSession = Depends(get_session)):
    try:
        return await service.send_message(session, member.id, data.content, data.document_ids)
    except ValueError as e:                     # document_ids không thuộc member
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("", response_model=list[ChatMessageOut])
async def history(member: FamilyMember = Depends(readable_member), session: AsyncSession = Depends(get_session)):
    return await service.get_history(session, member.id)
