from pydantic_settings import BaseSettings, SettingsConfigDict

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
    storage_dir: str = "storage"
    timezone: str = "Asia/Ho_Chi_Minh"
