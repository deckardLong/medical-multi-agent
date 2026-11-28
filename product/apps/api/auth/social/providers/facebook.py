import hashlib
import hmac
import httpx
from product.config import ProductEnv
from product.db.models import OAuthProvider
from ..errors import ProviderUnavailable, SocialAuthError
from ..profile import SocialProfile

env = ProductEnv()
# Không ghi số phiên bản (v2x.0): Graph API tự dùng phiên bản đặt trong App Dashboard,
# nên không bị lỗi khi một phiên bản cố định bị Meta ngừng hỗ trợ
GRAPH = "https://graph.facebook.com"


def _appsecret_proof(token: str) -> str:
    """Chữ ký HMAC kèm theo request, chứng minh request đến từ server có app secret."""
    secret = env.facebook_app_secret.get_secret_value().encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


async def verify_facebook(token: str) -> SocialProfile:
    if not (env.facebook_app_id and env.facebook_app_secret):
        raise SocialAuthError("Chưa cấu hình đăng nhập Facebook")
    app_token = f"{env.facebook_app_id}|{env.facebook_app_secret.get_secret_value()}"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Bước 1: token có hợp lệ và có ĐÚNG là cấp cho app này không (chặn token của app khác)
            dbg = await client.get(f"{GRAPH}/debug_token", params={"input_token": token, "access_token": app_token})
            data = dbg.json().get("data", {})
            if not data.get("is_valid") or str(data.get("app_id")) != env.facebook_app_id:
                raise SocialAuthError("Facebook access token không hợp lệ hoặc không cấp cho ứng dụng này")
            # Bước 2: lấy thông tin người dùng
            me = await client.get(f"{GRAPH}/me", params={"fields": "id,name,email", "access_token": token,
                                                         "appsecret_proof": _appsecret_proof(token)})
            if me.status_code != 200:
                raise SocialAuthError("Không đọc được thông tin tài khoản Facebook")
            info = me.json()
    except httpx.HTTPError as e:
        raise ProviderUnavailable("Không kết nối được Facebook") from e

    if info.get("id") != str(data.get("user_id")):
        raise SocialAuthError("Token không khớp người dùng")
    # Facebook không trả cờ xác minh email → luôn coi là chưa xác minh, không dùng để tự gộp tài khoản
    return SocialProfile(provider=OAuthProvider.FACEBOOK, subject=info["id"], email=info.get("email"),
                         email_verified=False, name=info.get("name"))