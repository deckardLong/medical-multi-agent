from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from product.db.models import OAuthAccount, OAuthProvider
from product.db.session import get_session
from product.apps.api.auth.deps import get_current_user
from product.apps.api.auth.schemas import TokenOut
from product.apps.api.auth.security import create_access_token
from . import service
from .errors import ProviderUnavailable, SocialAuthError
from .profile import SocialProfile
from .providers import VERIFIERS
from .schemas import LinkedAccountOut, SocialTokenIn

router = APIRouter(prefix="/auth/social", tags=["auth-social"])


async def _verify(provider: OAuthProvider, token: str) -> SocialProfile:
    try:
        return await VERIFIERS[provider](token)
    except SocialAuthError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))
    except ProviderUnavailable as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))


@router.post("/{provider}", response_model=TokenOut)
async def social_login(provider: OAuthProvider, data: SocialTokenIn, session: AsyncSession = Depends(get_session)):
    profile = await _verify(provider, data.token)
    try:
        user = await service.login_or_register(session, profile)
    except service.MissingEmail as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    except service.EmailConflict as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/{provider}/link", status_code=status.HTTP_204_NO_CONTENT)
async def social_link(provider: OAuthProvider, data: SocialTokenIn, user=Depends(get_current_user),
                      session: AsyncSession = Depends(get_session)):
    profile = await _verify(provider, data.token)
    try:
        await service.link(session, user, profile)
    except service.AlreadyLinked as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))

@router.get("/accounts", response_model=list[LinkedAccountOut])
async def linked_accounts(user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Các tài khoản Google/Facebook đã gắn với người dùng đang đăng nhập (để giao diện hiện trạng thái liên kết)."""
    rows = await session.scalars(select(OAuthAccount).where(OAuthAccount.user_id == user.id))
    return [LinkedAccountOut(provider=r.provider.value, email=r.email) for r in rows]
