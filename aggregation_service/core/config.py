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


class RedisConfig(BaseModel):
    host: str
    port: int
    password: str
    db: int

    @property
    def sync_url(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"

class RateLimitConfig(BaseModel):
    enabled: bool = True
    requests_per_minute: int = 100
    requests_per_hour: int = 100
    trusted_origins: list[str] = []


class SentryConfig(BaseModel):
    dsn: str = ""
    environment: str = "production"
    release: str = ""
    enabled: bool = True
    sample_rate: float = 1.0
    traces_sample_rate: float = 0.0


class ArbitrageConfig(BaseModel):
    price_threshold: float = 0.97       # макс. сумма цен YES+NO для входа в арбитраж
    min_size: float = 25                # мин. размер контракта в стакане
    threshold_distance: float = 0.7     # макс. embedding-дистанция между парами
    threshold_final_score: float = 0.7  # мин. score схожести пары
    max_workers: int = 4                # воркеры ProcessPoolExecutor
    cache_ttl: int = 60                 # TTL кэша арбитража в Redis (сек)
    scan_interval: float = 2           # интервал сканирования воркера (сек)


class PairPollingConfig(BaseModel):
    similarity_threshold: float = 0.7  # мин. final_score для сохранения пары
    max_distance: float = 0.5          # макс. embedding-дистанция при поиске кандидатов
    batch_limit: int = 60000           # маркетов за один проход поллинга
    poll_interval: int = 30            # пауза между проходами (сек)
    restart_delay: int = 5             # пауза перед рестартом при краше (сек)


class JWTConfig(BaseModel):
    secret_key: str
    algorithm: str = "HS256"


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    db: DatabaseConfig
    redis: RedisConfig
    jwt: JWTConfig
    rate_limit: RateLimitConfig = RateLimitConfig()
    sentry: SentryConfig = SentryConfig()
    arbitrage: ArbitrageConfig = ArbitrageConfig()
    pair_polling: PairPollingConfig = PairPollingConfig()
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]
    uvicorn_workers: int = 2

settings = Settings()
