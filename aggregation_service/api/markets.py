
import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.database import get_ro_session, get_rw_session_dep
from core.repositories.market_repository import MarketRepository
from core.repositories.orderbook_repository import OrderbookRepository
from core.repositories.pair_repository import PairRepository
from core.schemas.markets import DeleteMarketsBody, MarketPair, MarketShort
from core.schemas.orderbooks import OrderbookOut
from services.market_service.service import MarketService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("/platforms")
async def get_platforms(db_session: AsyncSession = Depends(get_ro_session)):
    repo = MarketRepository(session=db_session)
    return await repo.get_platforms()


@router.post("/add_pair")
async def add_pair(
    markets_ids_list: list[list],
    db_session: AsyncSession = Depends(get_rw_session_dep),
):
    repo = PairRepository(session=db_session)
    return await repo.add_pair(markets_ids_list=markets_ids_list)


@router.delete("/delete")
async def delete_pair(
    body: DeleteMarketsBody,
    db_session: AsyncSession = Depends(get_rw_session_dep),
):
    repo = PairRepository(session=db_session)
    await repo.delete_pair(market_ids=body.market_ids)


@router.get("/market/{common_id}")
async def find_market(
    platform: str,
    common_id: str,
    db_session: AsyncSession = Depends(get_ro_session),
):
    service = MarketService(
        common_id=common_id,
        platform=platform,
        session=db_session,
    )
    markets = await service.search()
    return [
        MarketShort(
            platform=market.platform,
            platform_market_id=market.platform_market_id,
            title=market.title,
            description=market.description,
            close_time=market.close_time,
        )
        for market in markets
    ]


@router.get("/search")
async def search(
    text: str,
    platform: str,
    db_session: AsyncSession = Depends(get_ro_session),
):
    repo = MarketRepository(session=db_session)
    markets = await repo.search_by_query(
        text=text.lower(),
        platform=platform,
    )
    return [
        MarketShort(
            platform=market.platform,
            platform_market_id=market.platform_market_id,
            title=market.title,
            description=market.description,
            close_time=market.close_time,
        )
        for market in markets
    ]


@router.get("/pairs")
async def get_market_pairs(
    db_session: AsyncSession = Depends(get_ro_session),
    max_distance: float = Query(0.7, ge=0.0, le=1.0),
    final_score: float = Query(0.7, ge=0.0, le=1.0),
    limit: int = Query(500, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[MarketPair]:
    pair_repo = PairRepository(session=db_session)

    pairs_with_markets = await pair_repo.get_all_pairs_with_markets(
        threshold_distance=max_distance,
        threshold_final_score=final_score,
        limit=limit,
        offset=offset,
    )
    logger.info("get_market_pairs_fetched", total_pairs=len(pairs_with_markets))

    result: list[MarketPair] = []

    for pair, markets in pairs_with_markets:
        if len(markets) != 2:
            logger.warning(
                "unexpected_number_of_markets_in_pair",
                pair_id=pair.id,
                market_count=len(markets),
            )
            continue

        market_a, market_b = markets

        result.append(
            MarketPair(
                market_a=MarketShort(
                    platform=market_a.platform,
                    platform_market_id=market_a.platform_market_id,
                    title=market_a.title,
                    description=market_a.description,
                    close_time=market_a.close_time,
                ),
                market_b=MarketShort(
                    platform=market_b.platform,
                    platform_market_id=market_b.platform_market_id,
                    title=market_b.title,
                    description=market_b.description,
                    close_time=market_b.close_time,
                ),
                final_score=pair.final_score,
                distance=pair.distance,
                channels={
                    "title": pair.title_channel_score,
                    "semantic": pair.semantic_channel_score,
                },
            )
        )

    logger.info("get_market_pairs_finished", len_pairs=len(result))
    return result


@router.get("/orderbooks", response_model=list[OrderbookOut])
async def get_orderbooks(
    platform_market_ids: list[str] = Query(...),
    db_session: AsyncSession = Depends(get_ro_session),
) -> list[OrderbookOut]:
    repo = OrderbookRepository(session=db_session)
    orderbooks = await repo.get_by_platform_market_ids(platform_market_ids)
    return [
        OrderbookOut(
            platform_market_id=ob.platform_market_id,
            orderbook=ob.orderbook,
            updated_at=ob.updated_at,
        )
        for ob in orderbooks
    ]
