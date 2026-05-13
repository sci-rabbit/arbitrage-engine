from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models.orderbooks import Orderbook


class OrderbookAsyncRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_orderbook(
        self,
        platform_market_id: str,
        orderbook: Optional[Dict[str, Any]],
    ) -> Orderbook:

        result = await self.session.execute(
            select(Orderbook).where(Orderbook.platform_market_id == platform_market_id)
        )
        obj = result.scalars().first()

        if obj is None:
            obj = Orderbook(platform_market_id=platform_market_id, orderbook=orderbook)
            self.session.add(obj)
            return obj

        if orderbook is None:
            obj.orderbook = None
            return obj

        existing = obj.orderbook
        if isinstance(existing, dict) and isinstance(orderbook, dict):
            merged = dict(existing)
            for k, v in orderbook.items():
                if v is not None:
                    merged[k] = v
            obj.orderbook = merged
        else:
            obj.orderbook = orderbook
        return obj


class OrderbookSyncRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_orderbook(
        self,
        platform_market_id: str,
        orderbook: Optional[Dict[str, Any]],
    ) -> Orderbook:
        obj = Orderbook(platform_market_id=platform_market_id, orderbook=orderbook)
        self.session.add(obj)
        self.session.flush()
        return obj

    def update_orderbook(
        self,
        platform_market_id: str,
        orderbook: Optional[Dict[str, Any]],
    ) -> Orderbook:
        obj = (
            self.session.query(Orderbook)
            .filter(Orderbook.platform_market_id == platform_market_id)
            .first()
        )

        if not obj:
            obj = self.create_orderbook(platform_market_id, orderbook)
            return obj


        if orderbook is None:
            obj.orderbook = None
            self.session.flush()
            return obj

        existing = obj.orderbook
        if isinstance(existing, dict) and isinstance(orderbook, dict):
            merged: Dict[str, Any] = dict(existing)
            for key, value in orderbook.items():
                if value is not None:
                    merged[key] = value
            obj.orderbook = merged
        else:
            obj.orderbook = orderbook

        self.session.flush()
        return obj
