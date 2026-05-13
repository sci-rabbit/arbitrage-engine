import re
import structlog
from datetime import datetime, timezone

from core.market_parsers.utils import parse_dt
from core.market_parsers.base_parser import BaseParser

logger = structlog.getLogger(__name__)


def _date_from_slug(slug: str):
    m = re.search(r'(\d{4}-\d{2}-\d{2})$', slug or "")
    if m:
        try:
            return datetime.strptime(m.group(1), '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


class PredictFunParser(BaseParser):

    @classmethod
    def parse_market(cls, raw: dict) -> dict:
        logger.info("PredictFun - Start parsing data")
        logger.debug("PredictFun - Data for debugging", raw=raw)

        # title - используем question или title
        title = raw.get("question") or raw.get("title") or ""
        normalized_title = title.lower()
        logger.debug(
            "PredictFun - ",
            title=title,
            normalize_title=normalized_title,
        )

        # outcomes - парсим из массива outcomes
        outcomes_raw = raw.get("outcomes", [])
        outcomes_parsed = None
        if outcomes_raw:
            # Преобразуем массив outcomes в структуру, похожую на другие парсеры
            outcome_names = [
                outcome.get("name") for outcome in outcomes_raw if outcome.get("name")
            ]
            if outcome_names:
                outcomes_parsed = {
                    "type": "binary" if len(outcome_names) == 2 else "multiple",
                    "labels": outcome_names,
                    "raw": outcomes_raw,
                }
                # Сохраняем полную информацию об outcomes для справки

        # token_ids или onChainIds - используем onChainId из outcomes и resolution
        token_ids = []
        # if outcomes_raw:
        #     for outcome in outcomes_raw:
        #         on_chain_id = outcome.get("onChainId")
        #         if on_chain_id:
        #             token_ids.append(on_chain_id)
        # resolution = raw.get("resolution", {})
        # resolution_on_chain_id = resolution.get("onChainId")
        # if resolution_on_chain_id and resolution_on_chain_id not in token_ids:
        #     token_ids.append(resolution_on_chain_id)

        # times
        open_time = parse_dt(raw.get("createdAt"))

        # category
        category = raw.get("categorySlug") or ""

        # For sports markets (outcomes have team data), parse event date from categorySlug
        is_sports = any(o.get("team") for o in outcomes_raw) if outcomes_raw else False
        close_time = _date_from_slug(category) if is_sports else None

        # description
        description = raw.get("description") or ""

        # event_id - можно использовать conditionId или oracleQuestionId
        event_id = raw.get("conditionId") or raw.get("oracleQuestionId") or ""

        return dict(
            platform="predict_fun",
            platform_market_id=str(raw.get("id")),
            event_id=event_id,
            event_slug=category,
            category=category,
            title=title,
            normalized_title=normalized_title,
            description=description.lower(),
            outcomes=outcomes_parsed,
            is_binary=(
                True
                if outcomes_parsed and outcomes_parsed.get("type") == "binary"
                else False
            ),
            token_ids=token_ids if token_ids else None,
            liquidity=None,  # В примере нет поля liquidity
            volume_24h=None,  # В примере нет поля volume_24h
            open_time=open_time,
            close_time=close_time,
            embedding=None,
            semantic_embedding=None,
            raw=raw,
        )
