import structlog

from services.similarity_service.aggregation.weighted_sum import aggregate
from services.similarity_service.stages.dataclass import PairItem

logger = structlog.getLogger(__name__)


class FinalScoreStage:
    name = "final_score"

    def __init__(self, threshold, weights):
        self.threshold = threshold
        self.weights = weights
        self.total = 0
        self.filtered = 0

    def process_batch(self, items: list[PairItem]):
        passed = []
        invalid = []

        for it in items:
            self.total += 1

            final = aggregate(it.channel_scores, self.weights)
            it.final_score = final

            if final < self.threshold:
                self.filtered += 1
                invalid.append({
                    "a_market_id": it.a.platform_market_id,
                    "b_market_id": it.b.platform_market_id,
                })
                continue

            passed.append({
                "a_market": it.a,
                "b_market": it.b,
                "min_distance": it.row["min_distance"],
                "final_score": round(final, 4),
                "channels": it.channel_scores,
                "cross_encoder": round(it.ce_score, 4),
                "a_id": getattr(it.a, "id", id(it.a)),
            })

        logger.info(
            "final_score_batch",
            batch=len(items),
            passed=len(passed),
            filtered=self.filtered,
        )

        return passed, invalid
