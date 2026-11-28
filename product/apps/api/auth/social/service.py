from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import OAuthAccount, User
from product.apps.api.members import service as members_service
from .profile import SocialProfile


class EmailConflict(Exception):
    """Email đã thuộc tài khoản khác, nhưng nhà cung cấp không chứng minh được quyền sở hữu email → 409."""


class MissingEmail(Exception):
    """Nhà cung cấp không trả email → 400."""


class AlreadyLinked(Exception):
    """Tài khoản mạng xã hội đã gắn với user khác, hoặc user đã gắn một tài khoản khác cùng nhà cung cấp → 409."""


async def _find_link(session: AsyncSession, p: SocialProfile) -> OAuthAccount | None:
    return await session.scalar(select(OAuthAccount).where(
        OAuthAccount.provider == p.provider, OAuthAccount.subject == p.subject))


def _link_row(user: User, p: SocialProfile) -> OAuthAccount:
    return OAuthAccount(user_id=user.id, provider=p.provider, subject=p.subject, email=p.email)


async def _create_user(session: AsyncSession, p: SocialProfile) -> User:
    user = User(email=p.email, password_hash=None, email_verified=p.email_verified,
                display_name=p.name or p.email.split("@")[0])
    session.add(user)
    await session.flush()                      # cần user.id trước khi tạo dòng liên kết
    session.add(_link_row(user, p))
    # User + liên kết + gia đình + thành viên "self" trong MỘT transaction (create_family_with_self commit tất cả),
    # như /auth/register: commit riêng thì lỗi ở bước tạo gia đình để lại user không có gia đình (dashboard 404)
    await members_service.create_family_with_self(session, user)
    await session.refresh(user)
    return user


async def login_or_register(session: AsyncSession, p: SocialProfile) -> User:
    # 1. Đã liên kết từ trước → đăng nhập luôn (tra theo subject, không tra theo email)
    link = await _find_link(session, p)
    if link:
        return await session.get(User, link.user_id)

    if not p.email:
        raise MissingEmail("Tài khoản không cung cấp email, hãy dùng cách đăng nhập khác")

    # 2. Email chưa có trong hệ thống → tạo tài khoản mới
    existing = await session.scalar(select(User).where(User.email == p.email))
    if existing is None:
        return await _create_user(session, p)

    # 3. Email đã có, nhưng nhà cung cấp không chứng minh được quyền sở hữu email → không tự gộp
    if not p.email_verified:
        raise EmailConflict("Email đã được dùng. Hãy đăng nhập bằng cách cũ rồi liên kết trong phần cài đặt")

    # 4. Email đã được chứng minh. Nếu tài khoản cũ chưa từng xác minh email thì mọi cách đăng nhập cũ
    #    (mật khẩu, Facebook) đều do người CHƯA chứng minh sở hữu email tạo ra → gỡ hết (chặn chiếm tài khoản trước)
    if not existing.email_verified:
        existing.password_hash = None
        await session.execute(delete(OAuthAccount).where(OAuthAccount.user_id == existing.id))
    existing.email_verified = True
    session.add(_link_row(existing, p))
    await session.commit()
    return existing


async def link(session: AsyncSession, user: User, p: SocialProfile) -> None:
    """User đang đăng nhập tự gắn thêm Google/Facebook. Không cần khớp email: người này đã
    chứng minh sở hữu cả tài khoản hệ thống (JWT) lẫn tài khoản mạng xã hội (token)."""
    found = await _find_link(session, p)
    if found:
        if found.user_id != user.id:
            raise AlreadyLinked("Tài khoản này đã gắn với một người dùng khác")
        return                                   # đã gắn rồi, gọi lại không lỗi (idempotent)
    session.add(_link_row(user, p))
    try:
        await session.commit()
    except IntegrityError:                       # vi phạm uq_oauth_user_provider
        await session.rollback()
        raise AlreadyLinked(f"Bạn đã liên kết một tài khoản {p.provider.value} khác")