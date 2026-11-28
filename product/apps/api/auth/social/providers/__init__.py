from product.db.models import OAuthProvider
from .facebook import verify_facebook
from .google import verify_google

VERIFIERS = {OAuthProvider.GOOGLE: verify_google, OAuthProvider.FACEBOOK: verify_facebook}