# product/apps/api/auth/social/schemas.py
from pydantic import BaseModel


class SocialTokenIn(BaseModel):
    # Google: ID token (JWT). Facebook: access token.
    token: str

class LinkedAccountOut(BaseModel):
    provider: str
    email: str | None = None          # email của tài khoản mạng xã hội (có thể khác email đăng nhập)
