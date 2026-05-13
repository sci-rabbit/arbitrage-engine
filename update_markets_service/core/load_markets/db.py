from typing import List

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from core.models import Market

logger = structlog.getLogger(__name__)


async def batch_commit(
    db_session: AsyncSession,
    results: List[Market],
):

    if not results:
        return

    batch = []

    for market in results:
        batch.append(market)
        if len(batch) >= 50:
            db_session.add_all(batch)
            await db_session.flush()
            batch.clear()
            batch = []

    if batch:
        db_session.add_all(batch)
        await db_session.flush()
