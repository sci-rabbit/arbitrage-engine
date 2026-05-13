import structlog

from services.similarity_service.stages.dataclass import PairItem

logger = structlog.getLogger(__name__)

class ChannelScoreStage:
    name = "channel_scores"

    def __init__(self, scorer, batch_size=200):
        self.scorer = scorer
        self.batch_size = batch_size
        self.total = 0
        self.failed = 0

    def process_batch(self, items: list[PairItem]):
        pairs = [(it.a, it.b) for it in items]

        scores = self.scorer.compute_channel_scores_batch(pairs)

        passed = []
        invalid = []

        for it, sc in zip(items, scores):
            self.total += 1
            if sc is None:
                self.failed += 1
                invalid.append(
                    {
                        "a_market_id": it.a.platform_market_id,
                        "b_market_id": it.b.platform_market_id,
                    }
                )
            else:
                it.channel_scores = sc
                passed.append(it)

        logger.info(
            "channel_scores_batch",
            batch=len(items),
            passed=len(passed),
            failed=len(invalid),
            total=self.total,
            failed_total=self.failed,
        )

        return passed, invalid
