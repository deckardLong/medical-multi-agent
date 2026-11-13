from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import FamilyMember
from product.db.session import get_session
from product.apps.api.errors import ConflictError
from product.apps.api.members.deps import readable_member, writable_member
from . import service
from .schemas import RecordConfirmIn, RecordIn, RecordOut, StatusFilter

router = APIRouter(prefix="/members/{member_id}/records", tags=["records"])


def _http(e: Exception) -> HTTPException:
    if isinstance(e, LookupError):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    if isinstance(e, ConflictError):
        return HTTPException(status.HTTP_409_CONFLICT, str(e))
    return HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.get("", response_model=list[RecordOut])
async def list_records(status_filter: StatusFilter = StatusFilter.ALL, member: FamilyMember = Depends(readable_member),
                       session: AsyncSession = Depends(get_session)):
    return await service.list_records(session, member.id, status_filter)


@router.post("", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
async def create_record(data: RecordIn, member: FamilyMember = Depends(writable_member),
                        session: AsyncSession = Depends(get_session)):
    """Người dùng tự nhập một mục hồ sơ — có hiệu lực ngay."""
    try:
        return await service.create_record(session, member.id, data.kind, data.payload)
    except (LookupError, ValueError) as e:
        raise _http(e)


@router.post("/{record_id}/confirm", response_model=RecordOut)
async def confirm_record(record_id: UUID, data: RecordConfirmIn | None = None,
                         member: FamilyMember = Depends(writable_member), session: AsyncSession = Depends(get_session)):
    """Xác nhận đề xuất của agent; gửi `payload` đã sửa nếu đề xuất còn trường "(cần kiểm tra)"."""
    try:
        return await service.confirm_record(session, member.id, record_id, data.payload if data else None)
    except (LookupError, ValueError) as e:
        raise _http(e)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(record_id: UUID, member: FamilyMember = Depends(writable_member),
                        session: AsyncSession = Depends(get_session)):
    try:
        await service.delete_record(session, member.id, record_id)
    except LookupError as e:
        raise _http(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
