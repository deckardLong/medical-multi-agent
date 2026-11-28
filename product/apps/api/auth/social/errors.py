class SocialAuthError(Exception):
    """Token sai, hết hạn, hoặc không cấp cho app này → 401."""

class ProviderUnavailable(Exception):
    """Không gọi được Google/Facebook (mạng, timeout) → 503, không phải lỗi của người dùng."""