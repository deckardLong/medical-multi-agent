import asyncio
from google.auth import exceptions as google_exc
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from product.config import ProductEnv
from product.db.models import OAuthProvider
from ..errors import ProviderUnavailable, SocialAuthError
from ..profile import SocialProfile

env = ProductEnv()
_request = google_requests.Request()

def _verify_sync(token: str) -> dict:
    claims = id_token.verify_oauth2_token(token, _request)
    if claims.get("aud") not in env.google_client_ids:
        raise SocialAuthError("Google ID token không cấp cho ứng dụng này")
    return claims


async def verify_google(token: str) -> SocialProfile:
    if not env.google_client_ids:
        raise SocialAuthError("Chưa cấu hình đăng nhập Google")
    try:
        claims = await asyncio.to_thread(_verify_sync, token)   
    except google_exc.TransportError as e:
        raise ProviderUnavailable("Không kết nối được Google") from e
    except ValueError as e:
        raise SocialAuthError("Google ID token không hợp lệ hoặc đã hết hạn") from e
    return SocialProfile(provider=OAuthProvider.GOOGLE, subject=claims["sub"], email=claims.get("email"),
                         email_verified=bool(claims.get("email_verified")), name=claims.get("name"))