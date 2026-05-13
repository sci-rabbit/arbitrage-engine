import asyncio
from sqlalchemy import delete, func, text
from sqlalchemy.dialects.postgresql import array

from core.models import Market
from core.models import Pair
from core.models.database import get_rw_session


ORPHAN_PAIRS_SQL = """
DELETE FROM pairs p
WHERE EXISTS (
    SELECT 1
    FROM jsonb_array_elements_text(p.market_ids) mid
    LEFT JOIN markets m
        ON m.platform_market_id = mid
    WHERE m.platform_market_id IS NULL
);
"""


async def cleanup_task(session_factory):
    while True:
        try:
            async with session_factory() as session:
                async with session.begin():

                    # 1️⃣ Удаляем expired markets
                    delete_markets_stmt = (
                        delete(Market)
                        .where(
                            Market.close_time.is_not(None),
                            Market.close_time < func.now()
                        )
                        .returning(Market.platform_market_id)
                    )

                    result = await session.execute(delete_markets_stmt)
                    deleted_ids = [row[0] for row in result.fetchall()]

                    if deleted_ids:
                        print(f"Deleted markets: {len(deleted_ids)}")

                        # 2️⃣ Удаляем pairs по удалённым market_id
                        delete_pairs_stmt = (
                            delete(Pair)
                            .where(
                                Pair.market_ids.op("?|")(
                                    array(deleted_ids)
                                )
                            )
                        )

                        result_pairs = await session.execute(delete_pairs_stmt)
                        print(f"Deleted pairs by expired markets: {result_pairs.rowcount}")

                    # 3️⃣ Удаляем осиротевшие pairs (на всякий случай)
                    orphan_result = await session.execute(text(ORPHAN_PAIRS_SQL))
                    print(f"Deleted orphan pairs: {orphan_result.rowcount}")

        except Exception as e:
            print("Cleanup error:", e)

        await asyncio.sleep(60 * 60 * 24)



async def main():
    await cleanup_task(get_rw_session)


if __name__ == '__main__':
    asyncio.run(main())
