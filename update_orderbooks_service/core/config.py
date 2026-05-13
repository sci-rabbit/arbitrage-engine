import datetime
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.kalshi_utils import load_private_key_from_file, sign_pss_text

BASE_DIR = Path(__file__).resolve().parent.parent


class KalshiConfig(BaseModel):
    url: str = "https://api.elections.kalshi.com/trade-api/v2/markets"
    ws_url: str = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    limit: int = 1000
    status: str = "open"
    volume_filter: int = 10000
    max_concurrency: int = 5
    proxy_url: str = None
    access_key: str
    private_key_path: str

    def get_headers(self, method: str = "GET", path: str = "/") -> dict:
        current_time = datetime.datetime.now()
        timestamp = current_time.timestamp()
        current_time_milliseconds = int(timestamp * 1000)
        timestamp_str = str(current_time_milliseconds)

        key_path = Path(self.private_key_path)
        if not key_path.is_absolute():
            key_path = BASE_DIR / key_path
        private_key = load_private_key_from_file(str(key_path))

        path_without_query = path.split("?")[0]
        msg_string = timestamp_str + method + path_without_query
        sig = sign_pss_text(private_key, msg_string)

        return {
            "KALSHI-ACCESS-KEY": self.access_key,
            "KALSHI-ACCESS-SIGNATURE": sig,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }


class PolymarketConfig(BaseModel):
    url: str = "https://gamma-api.polymarket.com/markets"
    order_book_url: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    volume_filter: int = 10000
    limit: int = 10000
    closed: str = "false"
    proxy_url: str = None


class PredictFunConfig(BaseModel):
    url: str = "https://api.predict.fun/v1/markets"
    ws_url: str = "wss://ws.predict.fun/ws"
    api_key: str
    proxy_url: str = None

    def get_headers(self) -> dict:
        return {
            "x-api-key": self.api_key,
        }


class WebSocketWorker:
    BATCH_SIZE: int = 100
    UPDATE_INTERVAL: int = 0.5
    MARKETS_REFRESH_INTERVAL: int = 60
    UPDATES_QUEUE_MAX_SIZE: int = 10_000
    NEW_MARKETS_QUEUE_MAX_SIZE: int = 1_000


class DatabaseConfig(BaseModel):
    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 1000
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
        extra="ignore",
    )
    kalshi: KalshiConfig
    polymarket: PolymarketConfig
    predict_fun: PredictFunConfig
    db: DatabaseConfig
    sentry_dsn: str = ""
    env: str = "production"
    log_level: str = "INFO"

    ws_worker: WebSocketWorker = WebSocketWorker()


settings = Settings()
