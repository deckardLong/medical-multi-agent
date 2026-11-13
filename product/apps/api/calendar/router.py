from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import FamilyMember
from product.db.session import get_session
from product.apps.api.errors import ConflictError
from product.apps.api.members.deps import readable_member, writable_member
from . import service
from .schemas import EventIn, EventOut, OccurrenceOut

router = APIRouter(prefix="/members/{member_id}/calendar", tags=["calendar"])


def _http(e: Exception) -> HTTPException:
    if isinstance(e, LookupError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    if isinstance(e, ConflictError):
        return HTTPException(status.HTTP_409_CONFLICT, str(e))
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("", response_model=list[OccurrenceOut])
async def list_occurrences(start: datetime | None = None, end: datetime | None = None, include_pending: bool = False,
                           member: FamilyMember = Depends(readable_member),
                           session: AsyncSession = Depends(get_session)):
    """Các lần xảy ra trong [start, end] (mặc định 30 ngày tới); lịch lặp được khai triển thành từng lần."""
    try:
        return await service.list_occurrences(session, member.id, start, end, include_pending)
    except ValueError as e:
        raise _http(e)


@router.get("/pending", response_model=list[EventOut])
async def list_pending(member: FamilyMember = Depends(readable_member), session: AsyncSession = Depends(get_session)):
    return await service.list_pending(session, member.id)


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(data: EventIn, member: FamilyMember = Depends(writable_member),
                       session: AsyncSession = Depends(get_session)):
    """Người dùng tự tạo lịch — có hiệu lực ngay."""
    try:
        return await service.create_event(session, member.id, data)
    except ValueError as e:
        raise _http(e)


@router.post("/{event_id}/confirm", response_model=EventOut)
async def confirm_event(event_id: UUID, member: FamilyMember = Depends(writable_member),
                        session: AsyncSession = Depends(get_session)):
    try:
        return await service.confirm_event(session, member.id, event_id)
    except (LookupError, ValueError) as e:
        raise _http(e)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(event_id: UUID, member: FamilyMember = Depends(writable_member),
                       session: AsyncSession = Depends(get_session)):
    try:
        await service.delete_event(session, member.id, event_id)
    except LookupError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
