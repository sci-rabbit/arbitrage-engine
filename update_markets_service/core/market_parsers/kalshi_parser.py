import structlog

from core.market_parsers.utils import (
    parse_dt,
)

from core.market_parsers.base_parser import BaseParser

logger = structlog.getLogger(__name__)


class KalshiParser(BaseParser):

    @classmethod
    def parse_market(cls, raw: dict) -> dict:
        m = raw.get("market", raw)

        logger.info("Kalshi - Start parsing data")
        logger.debug("Kalshi - Data for debugging", raw=m)

        # title
        title = m.get("title") or ""
        normalized_title = title.lower()
        logger.info(
            "Kalshi - ",
            title=title,
            normalize_title=normalized_title,
        )

        # outcomes — Kalshi бинарные рынки → yes/no
        outcomes = {
            "type": "binary",
            "labels": [m.get("yes_sub_title") or "Yes", m.get("no_sub_title") or "No"],
        }

        # description
        rules_primary = m.get("rules_primary") or ""
        rules_secondary = m.get("rules_secondary") or ""
        description = (
            rules_primary + "\n" + rules_secondary if rules_secondary else rules_primary
        )

        # times
        open_time = parse_dt(m.get("open_time"))
        close_time = parse_dt(m.get("close_time"))

        return dict(
            platform="kalshi",
            platform_market_id=m.get("ticker"),
            event_id=m.get("event_ticker"),
            event_slug=None,
            series_ticker=m.get("series_ticker"),  # Будет передано из загрузчика
            category=m.get("category") or "",
            title=title,
            normalized_title=normalized_title,
            description=description.lower(),
            outcomes=outcomes,
            is_binary=True,
            liquidity=(
                float(m.get("liquidity")) if m.get("liquidity") is not None else None
            ),
            volume_24h=(
                float(m.get("volume_24h")) if m.get("volume_24h") is not None else None
            ),
            open_time=open_time,
            close_time=close_time,
            embedding=None,
            semantic_embedding=None,
            raw=raw,
        )
