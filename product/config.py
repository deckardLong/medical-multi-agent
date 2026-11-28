from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, field_validator

class ProductEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PRODUCT_", extra="ignore")
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/product"
    # Origin frontend được gọi API từ trình duyệt, cách nhau dấu phẩy (vd "https://aurelia.vercel.app").
    # Trống = không bật CORS (dev dùng Vite proxy cùng origin).
    cors_origins: str = ""
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24

    # ======= LLM Model =======
    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = "ollama"
    llm_model: str = "qwen2.5:7b-instruct"

    tavily_api_key: str = ""
    vlm_model: str = "qwen2.5vl:7b"
    # Model VLM cho agent vlm_transcribe; nên khác vlm_model để 2 lần đọc không sai cùng kiểu. Trống = dùng vlm_model
    vlm_transcribe_model: str | None = None
    storage_dir: str = "storage"
    timezone: str = "Asia/Ho_Chi_Minh"

    # ======= SMTP =======
    smtp_host: str | None = None          # None: job tự tắt, log cảnh báo — giống cách xử lý tavily_api_key
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str = "no-reply@example.com"

    reminder_lead_minutes: int = 60       # nhắc trước bao nhiêu phút
    reminder_scan_interval_minutes: int = 5

     # ======= OAuth =======
    google_client_ids: list[str] = []          # web, Android, iOS mỗi nền tảng có một client ID riêng
    facebook_app_id: str | None = None
    facebook_app_secret: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def _async_driver(cls, v: str) -> str:
        # Render/Heroku cấp URL dạng postgres:// hoặc postgresql:// → app cần driver asyncpg
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+asyncpg://" + v[len(prefix):]
        return v

    @property
    def sync_database_url(self) -> str:
        """Cùng database, driver psycopg2 cho Alembic (migration chạy đồng bộ)."""
        return self.database_url.replace("+asyncpg", "+psycopg2", 1)
