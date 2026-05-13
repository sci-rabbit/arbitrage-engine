from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class DatabaseConfig(BaseModel):
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 50
    max_overflow: int = 10
    user: str
    password: str
    host: str
    port: int
    name: str

    @property
    def sync_url(self) -> str:
        return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"


class JWTConfig(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    verify_token_expire_hours: int = 24
    reset_token_expire_hours: int = 1


class SentryConfig(BaseModel):
    dsn: str = ""
    environment: str = "dev"
    traces_sample_rate: float = 0.1
    enabled: bool = True


class AppConfig(BaseModel):
    debug: bool = True
    title: str = "User Service"
    version: str = "1.0.0"
    domain: str = "http://localhost:8000"


class EmailConfig(BaseModel):
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = "User Service"
    use_tls: bool = True

    @property
    def configured(self) -> bool:
        return bool(self.host and self.username and self.from_email)


class RedisConfig(BaseModel):
    url: str = "redis://localhost:6379"


class NOWPaymentsConfig(BaseModel):
    api_key: str = ""
    ipn_secret: str = ""
    webhook_base_url: str = ""
    base_url: str = "https://api.nowpayments.io"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.ipn_secret)


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    db: DatabaseConfig
    jwt: JWTConfig
    sentry: SentryConfig = SentryConfig()
    app: AppConfig = AppConfig()
    email: EmailConfig
    redis: RedisConfig = RedisConfig()
    nowpayments: NOWPaymentsConfig


settings = Settings()