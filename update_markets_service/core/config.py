from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class EmbeddingConfig(BaseModel):
    url: str = ""
    batch_size: int = 200
    max_concurrency: int = 8
    ws_url: str = ""
    poll_interval: int = 60


class KalshiConfig(BaseModel):
    url: str = "https://api.elections.kalshi.com/trade-api/v2/markets"
    events_url: str = "https://api.elections.kalshi.com/trade-api/v2/events"
    limit: int = 1000
    status: str = "open"
    volume_filter: int = 500
    poll_interval: int = 60
    max_concurrency: int = 3
    proxy_url: str


class PolymarketConfig(BaseModel):
    url: str = "https://gamma-api.polymarket.com/markets"
    order_book_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    volume_filter: int = 500
    limit: int = 500
    closed: str = "false"
    poll_interval: int = 60
    max_concurrency: int = 10
    proxy_url: str


class PredictFunConfig(BaseModel):
    api_key: str
    url: str = "https://api.predict.fun/v1/markets"
    orderbook_url: str = "https://api.predict.fun/v1/markets/{market_id}/orderbook"
    poll_interval: int = 60
    max_concurrency: int = 1
    proxy_url: str

    @staticmethod
    def get_orderbook_url(market_id: str) -> str:
        return PredictFunConfig.orderbook_url.format(market_id=market_id)

    def get_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
        }


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


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )
    embedding: EmbeddingConfig = EmbeddingConfig()
    db: DatabaseConfig
    kalshi: KalshiConfig
    polymarket: PolymarketConfig
    predict_fun: PredictFunConfig
    sentry_dsn: str = ""
    env: str = "production"
    log_level: str = "INFO"


settings = Settings()

