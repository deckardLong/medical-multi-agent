from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import Family, FamilyMember, User

# Check whether it's owner
def is_owner(family: Family, user: User) -> bool:
    return family.owner_user_id == user.id

# Check permission to write
def can_write_member(member: FamilyMember, family: Family, user: User) -> bool:
    # If there is no account (other member in the family like baby, old people,...) => They will be mananged by owner
    if member.linked_user_id is None:
        return is_owner(family, user)
    return member.linked_user_id == user.id

# Check read permission
def can_read_member(member: FamilyMember, family: Family, user: User) -> bool:
    """Only owner account can read and write"""
    return can_write_member(member, family, user)

async def authorize_member(session: AsyncSession, member_id: UUID, user: User) -> FamilyMember:
    """ValueError nếu không có thành viên; PermissionError nếu user không được truy cập dữ liệu của thành viên này."""
    member = await session.get(FamilyMember, member_id)
    if member is None:
        raise ValueError("Không tìm thấy thành viên")
    family = await session.get(Family, member.family_id)
    if family is None or not can_write_member(member, family, user):
        raise PermissionError("Bạn không có quyền truy cập dữ liệu của thành viên này")
    return member