from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

class ProductEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PRODUCT_", extra="ignore")
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/product"
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
