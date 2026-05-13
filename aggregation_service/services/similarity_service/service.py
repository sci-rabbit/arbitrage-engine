import time
from typing import Optional

import structlog


from core.similarity.cross_encoder import CrossEncoderClient

from core.models.markets import market_from_row

from services.similarity_service.compute_scores import ComputeScores
from services.similarity_service.stages.channelscores_stage import ChannelScoreStage
from services.similarity_service.stages.dataclass import PairItem
from services.similarity_service.stages.finalscores_stage import FinalScoreStage
from services.similarity_service.stages.hardgates_stage import HardGateStage
from services.similarity_service.stages.nli_gate_stage import NLIGateStage
from services.similarity_service.stages.pipeline import SimilarityPipeline

logger = structlog.getLogger(__name__)


class MarketSimilarityService:
    """
    Финальный сервис для поиска похожих маркетов.
    1. Prefilter через repo.find_pairs (по embedding / semantic_embedding)
    2. Вычисление score через каналы (title + semantic)
    3. Агрегация score
    4. Отбор top N пар для каждого a_market
    """

    def __init__(
        self,
        repo,
        channels=None,
        weights=None,
        threshold=0.7,
        max_distance=0.7,
        cross_encoder_threshold: Optional[float] = 0.85,
    ):
        self.repo = repo
        self.threshold = threshold
        self.max_distance = max_distance
        self.weights = weights or {
            "title": 0.7,
            "semantic": 0.3,
        }
        self.scorer = ComputeScores(
            channels=channels or [],
            weights=weights
            or {
                "title": 0.7,
                "semantic": 0.3,
            },
        )
        # Используем переданный порог или threshold по умолчанию
        ce_threshold = (
            cross_encoder_threshold
            if cross_encoder_threshold is not None
            else threshold
        )
        self.cross_encoder = CrossEncoderClient(threshold=ce_threshold)

        logger.info(
            "MarketSimilarityService initialized",
            threshold=self.threshold,
            max_distance=self.max_distance,
            weights=self.weights,
            cross_encoder_threshold=ce_threshold,
        )

    def _validate_markets(self, a, b) -> bool:
        """Валидация входных данных."""
        if a is None or b is None:
            return False
        if not hasattr(a, "embedding") or not hasattr(b, "embedding"):
            return False
        if not hasattr(a, "normalized_title") or not hasattr(b, "normalized_title"):
            return False
        return True

    async def find_similar_pairs(
        self,
        limit=60000,
        offset=0,
        batch_size=200,
    ):
        start_ts = time.perf_counter()

        logger.info(
            "Similarity search started",
            limit=limit,
            offset=offset,
            threshold=self.threshold,
        )

        candidates = await self.repo.find_pairs(
            limit=limit,
            offset=offset,
            max_distance=self.max_distance,
        )

        # ---------- prepare ----------
        prepared = []
        for row in candidates:
            try:
                a = market_from_row("a", row)
                b = market_from_row("b", row)
                if self._validate_markets(a, b):
                    prepared.append((a, b, row))
            except Exception:
                continue

        if not prepared:
            return

        # ---------- cross encoder (batched once) ----------
        pairs_text = [
            ((a.normalized_title or ""), (b.normalized_title or ""))
            for a, b, _ in prepared
        ]
        ce_scores = self.cross_encoder.score_batch(pairs_text)

        filtered = []
        ce_invalid = []
        for (a, b, row), ce in zip(prepared, ce_scores):
            if ce >= self.cross_encoder.threshold:
                filtered.append((a, b, row, ce))
            else:
                ce_invalid.append({
                    "a_market_id": a.platform_market_id,
                    "b_market_id": b.platform_market_id,
                })

        if ce_invalid:
            yield {"stage": "cross_encoder", "invalid_pairs": ce_invalid}

        logger.info("After cross_encoder", passed=len(filtered), rejected=len(ce_invalid))

        pipeline = SimilarityPipeline(
            stages=[
                HardGateStage(),
                NLIGateStage(),
                ChannelScoreStage(self.scorer),
                FinalScoreStage(self.threshold, self.weights),
            ],
            batch_size=batch_size,
        )

        items = [PairItem(a=a, b=b, row=row, ce_score=ce) for a, b, row, ce in filtered]

        for out in pipeline.run(items):
            yield out

        elapsed = round(time.perf_counter() - start_ts, 3)
        logger.info("Similarity search finished", elapsed_seconds=elapsed)