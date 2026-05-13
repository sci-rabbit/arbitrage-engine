import structlog
from celery import shared_task

from core.models.database import get_sync_rw_session
from core.repositories.orderbook_repository import OrderbookSyncRepository

log = structlog.get_logger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=2)
def update_orderbooks_task(self, platform: str, update_batch: dict):
    if platform not in ["polymarket", "kalshi", "predict_fun"]:
        log.error(
            "Unsupported platform",
            platform=platform,
            supported_platforms=["polymarket", "kalshi", "predict_fun"],
        )
        raise ValueError(f"Unsupported platform: {platform}")

    with get_sync_rw_session() as session:
        orderbook_repository = OrderbookSyncRepository(session=session)
        try:
            for market_id, orderbook in update_batch.items():
                result = orderbook_repository.update_orderbook(market_id, orderbook)
                if not result:
                    log.warning(
                        "Market not found for orderbook update",
                        platform=platform,
                        market_id=market_id,
                    )

        except Exception as exc:
            log.error(
                "Error updating orderbooks",
                platform=platform,
                error=str(exc),
                exc_info=True,
            )
            raise self.retry(exc=exc)
