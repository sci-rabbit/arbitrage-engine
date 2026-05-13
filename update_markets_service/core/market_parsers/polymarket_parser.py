import structlog

from core.market_parsers.utils import (
    string_to_json,
    parse_dt,
)

from core.market_parsers.base_parser import BaseParser

logger = structlog.getLogger(__name__)


class PolyMarketParser(BaseParser):

    @classmethod
    def parse_market(cls, raw: dict) -> dict:
        logger.info("Polymarket - Start parsing data")
        logger.debug("Polymarket - Data for debugging", raw=raw)

        # title
        title = raw.get("question") or ""
        normalized_title = title.lower()
        logger.debug(
            "Polymarket - ",
            title=title,
            normalize_title=normalized_title,
        )

        # outcomes
        outcomes_raw = raw.get("outcomes")
        outcomes_parsed = string_to_json(outcomes_raw, market_for_logging="Polymarket")

        token_ids = raw.get("clobTokenIds")

        # times — gameStartTime is more precise for sports, fallback to endDate
        open_time = parse_dt(raw.get("startDate"))
        close_time = parse_dt(raw.get("gameStartTime")) or parse_dt(raw.get("endDate"))

        # category
        category = raw.get("category") or ""

        # description
        description = raw.get("description") or ""

        events = raw.get("events") or []
        event_id = None
        event_slug = None
        if isinstance(events, list) and events:
            first = events[0] or {}
            event_id = first.get("id")
            event_slug = first.get("slug")

        return dict(
            platform="polymarket",
            platform_market_id=str(raw.get("id")),
            event_id=event_id,
            event_slug=event_slug,
            category=category,
            title=title,
            normalized_title=normalized_title,
            description=description.lower(),
            outcomes=outcomes_parsed,
            is_binary=True if outcomes_parsed and len(outcomes_parsed) == 2 else False,
            token_ids=token_ids,
            liquidity=(
                float(raw.get("liquidityNum")) if raw.get("liquidityNum") else None
            ),
            volume_24h=float(raw.get("volume24hr")) if raw.get("volume24hr") else None,
            open_time=open_time,
            close_time=close_time,
            embedding=None,
            semantic_embedding=None,
            raw=raw,
        )
