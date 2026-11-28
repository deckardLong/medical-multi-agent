from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import User
from .security import hash_password, verify_password, create_access_token
from .schemas import RegisterIn, LoginIn

async def register(session: AsyncSession, data: RegisterIn) -> User:
    """Tạo user + gia đình + thành viên "self" trong MỘT transaction: commit riêng từng bước thì lỗi ở bước sau
    để lại user không có gia đình (dashboard 404 vĩnh viễn)."""
    from product.apps.api.members.service import create_family_with_self
    existing = await session.scalar(select(User).where(User.email == data.email))
    if existing:
        raise ValueError("Email đã được đăng ký")
    user = User(email=data.email, password_hash=hash_password(data.password), display_name=data.display_name,
                last_name=data.last_name, first_name=data.first_name, date_of_birth=data.date_of_birth,
                gender=data.gender, phone=data.phone)
    session.add(user)
    await session.flush()
    await create_family_with_self(session, user)       # commit cả user lẫn gia đình
    await session.refresh(user)
    return user

async def login(session: AsyncSession, data: LoginIn) -> str:
    user = await session.scalar(select(User).where(User.email == data.email))
    if not user or not user.password_hash or not verify_password(data.password, user.password_hash):
        raise ValueError("Sai email hoặc mật khẩu")
    return create_access_token(str(user.id))
