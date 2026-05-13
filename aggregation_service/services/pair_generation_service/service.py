import time
from typing import Tuple

import structlog

from core.models.invalid_pairs import InvalidPair
from core.models.pair_a_index import PairAIndex
from core.models.market_pairs import Pair
from core.repositories.invalid_pairs_repository import InvalidPairRepository
from core.repositories.market_repository import MarketRepository
from services.similarity_service.service import MarketSimilarityService

logger = structlog.getLogger(__name__)

BATCH_SIZE = 200


class PairGenerationService:
    def __init__(
            self,
            similarity_service: MarketSimilarityService,
            market_repo: MarketRepository,
            invalid_pair_repo: InvalidPairRepository,
    ):
        self.similarity_service = similarity_service
        self.market_repo = market_repo
        self.invalid_pair_repo = invalid_pair_repo
        logger.info(
            "PairGenerationService initialized",
            batch_size=BATCH_SIZE,
        )


    async def generate_and_store(
            self,
            limit: int = 60_000,
            offset: int = 0,
            top_n_per_a: int = 1,
    ) -> int:
        start_ts = time.perf_counter()

        logger.info(
            "Pair generation started",
            limit=limit,
            offset=offset,
        )

        saved_valid = 0
        saved_invalid = 0
        candidates_count = 0

        batch_valid: list[Tuple[Pair, str]] = []
        batch_invalid: list[InvalidPair] = []

        async for batch in self.similarity_service.find_similar_pairs(
                limit=limit,
                offset=offset,
        ):
            candidates_count += len(batch.get("invalid_pairs", [])) + len(batch.get("valid_pairs", []))

            for item in batch.get("invalid_pairs", []):
                invalid_pair = InvalidPair(
                    a_market_id=item["a_market_id"],
                    b_market_id=item["b_market_id"],
                )
                batch_invalid.append(invalid_pair)

            for item in batch.get("valid_pairs", []):
                a = item["a_market"]
                b = item["b_market"]
                market_ids = sorted((a.platform_market_id, b.platform_market_id))

                pair = Pair(
                    market_ids=market_ids,
                    distance=item["min_distance"],
                    final_score=item["final_score"],
                    title_channel_score=item["channels"].get("title"),
                    semantic_channel_score=item["channels"].get("semantic"),
                )

                batch_valid.append((pair, a.platform_market_id))

            # --- flush batches по 200 ---
            if len(batch_valid) >= BATCH_SIZE:
                await self._flush_valid(batch_valid)
                saved_valid += len(batch_valid)
                logger.debug("Valid batch flushed", batch_size=len(batch_valid))
                batch_valid.clear()

            if len(batch_invalid) >= BATCH_SIZE:
                await self._flush_invalid(batch_invalid)
                saved_invalid += len(batch_invalid)
                logger.debug("Invalid batch flushed", batch_size=len(batch_invalid))
                batch_invalid.clear()

        # --- flush оставшиеся ---
        if batch_valid:
            await self._flush_valid(batch_valid)
            saved_valid += len(batch_valid)
            logger.debug("Final valid batch flushed", batch_size=len(batch_valid))

        if batch_invalid:
            await self._flush_invalid(batch_invalid)
            saved_invalid += len(batch_invalid)
            logger.debug("Final invalid batch flushed", batch_size=len(batch_invalid))

        # Выборка по pair_a_index: оставляем только top_n пар на каждый a_market_id
        deleted_excess = 0
        if top_n_per_a > 0:
            deleted_excess = await self.market_repo.cleanup_top_n(top_n=top_n_per_a)
            logger.info(
                "Cleanup by pair_a_index finished",
                top_n_per_a=top_n_per_a,
                deleted_pairs=deleted_excess,
            )

        elapsed = round(time.perf_counter() - start_ts, 3)
        logger.info(
            "Pair generation finished",
            saved_valid=saved_valid,
            saved_invalid=saved_invalid,
            candidates=candidates_count,
            deleted_excess=deleted_excess,
            elapsed_seconds=elapsed,
        )

        return saved_valid + saved_invalid

    # ------------------------------------------------------
    # Отдельные методы flush
    # ------------------------------------------------------

    async def _flush_valid(self, batch: list[Tuple[Pair, str]]) -> None:
        try:
            for pair, _ in batch:
                self.market_repo.session.add(pair)
            await self.market_repo.session.flush()  # один round-trip, все pair.id заполнены
            for pair, a_market_id in batch:
                self.market_repo.session.add(PairAIndex(
                    pair_id=pair.id,
                    a_market_id=a_market_id,
                    final_score=pair.final_score,
                ))
            await self.market_repo.session.commit()
        except Exception:
            logger.exception(
                "Failed to flush valid pair batch",
                batch_size=len(batch),
            )
            await self.market_repo.session.rollback()
            raise

    async def _flush_invalid(self, batch: list[InvalidPair]) -> None:
        try:
            for invalid_pair in batch:
                self.invalid_pair_repo.session.add(invalid_pair)
            await self.invalid_pair_repo.session.commit()
        except Exception:
            logger.exception(
                "Failed to flush invalid pair batch",
                batch_size=len(batch),
            )
            await self.invalid_pair_repo.session.rollback()
            raise
