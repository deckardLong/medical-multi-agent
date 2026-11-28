from dataclasses import dataclass
from product.db.models import OAuthProvider

@dataclass(frozen=True)
class SocialProfile:
    provider: OAuthProvider
    subject: str
    email: str | None
    email_verified: bool
    name: str | None