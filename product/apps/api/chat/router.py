from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.session import get_session
from product.apps.api.auth.deps import get_current_user
from . import service
from .schemas import SendMessageIn, ChatMessageOut

router = APIRouter(prefix="/members/{member_id}/chat", tags=["chat"])

@router.post("", response_model=ChatMessageOut)
async def send(member_id: UUID, data: SendMessageIn, user=Depends(get_current_user),
              session: AsyncSession = Depends(get_session)):
    try:
        return await service.send_message(session, member_id, data.content, user)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))


@router.get("", response_model=list[ChatMessageOut])
async def history(member_id: UUID, user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    try:
        return await service.get_history(session, member_id, user)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    except PermissionError as e:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))