from pydantic_settings import BaseSettings, SettingsConfigDict

class ProductEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PRODUCT_", extra="ignore")
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/product"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24
