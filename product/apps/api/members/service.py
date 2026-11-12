from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import Family, FamilyMember, MemberType, Connection, ConnectionStatus, User
from .schemas import FamilyMemberIn

# Create family when register
async def create_family_with_self(session: AsyncSession, user: User) -> Family:
    """After register, assign user to a family, 1 user - family (family of only it's user)"""
    family = Family(owner_user_id=user.id, name=f"Gia đình của {user.display_name}")
    session.add(family)
    await session.flush()
    session.add(FamilyMember(family_id=family.id, member_type=MemberType.SELF, display_name=user.display_name, linked_user_id=user.id))

    await session.commit()
    await session.refresh(family)
    return family

# Get family
async def get_family_for_owner(session: AsyncSession, user: User) -> Family:
    """If user doesn't have family => Error"""
    family = await session.scalar(select(Family).where(Family.owner_user_id == user.id))
    if family is None:
        raise ValueError(f"Người dùng chưa có family - lỗi dữ liệu, phải tạo lúc đăng ký")
    return family

# List members
async def list_members(session: AsyncSession, family_id: UUID) -> list[FamilyMember]:
    rows = await session.scalars(select(FamilyMember).where(FamilyMember.family_id == family_id))
    return list(rows)

# Add member who doesn't have account
async def add_managed_member(session: AsyncSession, family: Family, data: FamilyMemberIn) -> FamilyMember:
    """Manage if account doesn't exist like baby, elder,..."""
    member = FamilyMember(family_id=family.id, member_type=data.member_type, display_name=data.display_name, dob=data.dob, linked_user_id=None)
    session.add(member)

    await session.commit()
    await session.refresh(member)
    return member

# Send connection
async def send_connection_request(session: AsyncSession, requester: User, target_email: str) -> Connection:
    target = await session.scalar(select(User).where(User.email == target_email))
    if target is None:
        raise ValueError(f"Không tìm thấy người dùng với email này")
    if target.id == requester.id:
        raise ValueError(f"Không thể tự kết bạn với chính mình")
    # If user exist
    existing = await session.scalar(select(Connection).where(
        Connection.requester_user_id == requester.id,
        Connection.target_user_id == target.id
    ))
    if existing:
        raise ValueError(f"Đã gửi lời mời trước đó")
    conn = Connection(requester_user_id=requester.id, target_user_id=target.id, status=ConnectionStatus.PENDING)
    session.add(conn)

    await session.commit()
    await session.refresh(conn)
    return conn

# Response connection
async def respond_connection(session: AsyncSession, connection_id: UUID, user: User, accept: bool) -> Connection:
    conn = await session.get(Connection, connection_id)
    if conn is None or conn.target_user_id != user.id:
        raise ValueError(f"Không tìm thấy lời mời hoặc bạn không phải là người nhận")
    conn.status = ConnectionStatus.ACCEPTED if accept else ConnectionStatus.DECLINED

    await session.commit()
    await session.refresh(conn)
    return conn

# Attach new member
async def attach_connection_as_member(session: AsyncSession, family: Family, user: User, connection_id: UUID, member_type: MemberType) -> FamilyMember:
    """Add new member accepted to a family, create FamilyMember with linked_user_id to that new member"""
    conn = await session.get(Connection, connection_id)
    if conn is None or conn.status != ConnectionStatus.ACCEPTED:
        raise ValueError(f"Kết bạn không tồn tại hoặc chưa được chấp nhận")
    if user.id not in (conn.requester_user_id, conn.target_user_id):
        raise ValueError(f"Bạn không thuộc kết bạn này")
    other_user_id = conn.target_user_id if conn.requester_user_id == user.id else conn.requester_user_id    
    other_user = await session.get(User, other_user_id)
    member = FamilyMember(family_id=family.id, member_type=member_type, display_name=other_user.display_name, linked_user_id=other_user_id)
    session.add(member)

    await session.commit()
    await session.refresh(member)
    return member

# Incoming
async def list_incoming_connections(session: AsyncSession, user: User) -> list[Connection]:
    rows = await session.scalars(select(Connection).where(
        Connection.target_user_id == user.id,
        Connection.status == ConnectionStatus.PENDING
    ))
    return list(rows)