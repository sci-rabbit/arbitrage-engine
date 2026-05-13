from datetime import datetime

import structlog

logger = structlog.getLogger(__name__)


def parse_dt(v):
    if not v:
        return None
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00"))
    except Exception:
        return None


def string_to_json(data: str | dict, market_for_logging: str):
    if isinstance(data, str):
        import json

        logger.info(
            "Outcomes has string type. Using json.loads",
            market=market_for_logging,
        )
        try:
            parsed = json.loads(data)
            return parsed
        except Exception as e:
            logger.error(
                "Error while parsing outcomes, json.loads failed",
                market_for_logging=market_for_logging,
                error=str(e),
                exc_info=True,
            )
    else:
        return data
