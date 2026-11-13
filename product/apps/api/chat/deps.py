from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.session import get_session
from product.db.models import Family, FamilyMember, User
from product.apps.api.auth.deps import get_current_user
from product.apps.api.members.permissions import can_read_member, can_write_member

async def _load(session: AsyncSession, member_id: UUID) -> tuple[FamilyMember, Family]:
    member = await session.get(FamilyMember, member_id)
    family = await session.get(Family, member.family_id) if member else None

    # If member & family = None => Error
    if member is None or family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy thành viên")
    return member, family

async def readable_member(member_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> FamilyMember:
    member, family = await _load(session, member_id)
    if not can_read_member(member, family, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy thành viên")
    return member

async def writable_member(member_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)) -> FamilyMember:
    member, family = await _load(session, member_id)
    if not can_write_member(member, family, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy thành viên")
    return member