from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import Family, FamilyMember, User
from product.db.session import get_session
from product.apps.api.auth.deps import get_current_user
from .permissions import can_read_member, can_write_member


async def _member_or_404(member_id: UUID, user: User, session: AsyncSession, check) -> FamilyMember:
    member = await session.get(FamilyMember, member_id)
    family = await session.get(Family, member.family_id) if member else None
    # Không có quyền cũng trả 404 (không phải 403) để người ngoài không dò được member_id nào tồn tại
    if member is None or family is None or not check(member, family, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy thành viên")
    return member


async def readable_member(member_id: UUID, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)) -> FamilyMember:
    return await _member_or_404(member_id, user, session, can_read_member)


async def writable_member(member_id: UUID, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)) -> FamilyMember:
    return await _member_or_404(member_id, user, session, can_write_member)
