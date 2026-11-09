from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import User
from .security import hash_password, verify_password, create_access_token
from .schemas import RegisterIn, LoginIn

async def register(session: AsyncSession, data: RegisterIn) -> User:
    existing = await session.scalar(select(User).where(User.email == data.email))
    if existing:
        raise ValueError("Email đã được đăng ký")
    user = User(email=data.email, password_hash=hash_password(data.password), display_name=data.display_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

async def login(session: AsyncSession, data: LoginIn) -> str:
    user = await session.scalar(select(User).where(User.email == data.email))
    if not user or not verify_password(data.password, user.password_hash):
        raise ValueError("Sai email hoặc mật khẩu")
    return create_access_token(str(user.id))