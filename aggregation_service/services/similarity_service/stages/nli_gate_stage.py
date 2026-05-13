import structlog

from core.similarity.nli_client import entailment_scores_batch
from services.similarity_service.stages.dataclass import PairItem

logger = structlog.getLogger(__name__)

ENTAILMENT_THRESHOLD = 0.5


class NLIGateStage:
    """
    Rejects pairs where one event logically entails the other.
    E.g. "qualify for final" entails "top 10" — not a valid arbitrage pair.
    Checks both directions: A→B and B→A.
    """
    name = "nli_gate"

    def __init__(self, threshold: float = ENTAILMENT_THRESHOLD):
        self.threshold = threshold
        self.total = 0
        self.failed = 0

    def process_batch(self, items: list[PairItem]):
        if not items:
            return [], []

        fwd_pairs = [
            (it.a.normalized_title or "", it.b.normalized_title or "")
            for it in items
        ]
        bwd_pairs = [
            (it.b.normalized_title or "", it.a.normalized_title or "")
            for it in items
        ]

        scores_fwd = entailment_scores_batch(fwd_pairs)
        scores_bwd = entailment_scores_batch(bwd_pairs)

        passed = []
        invalid = []

        for it, fwd, bwd in zip(items, scores_fwd, scores_bwd):
            self.total += 1
            if max(fwd, bwd) >= self.threshold:
                self.failed += 1
                logger.info(
                    "nli_gate_rejected",
                    a=it.a.normalized_title,
                    b=it.b.normalized_title,
                    entailment_fwd=round(fwd, 3),
                    entailment_bwd=round(bwd, 3),
                )
                invalid.append({
                    "a_market_id": it.a.platform_market_id,
                    "b_market_id": it.b.platform_market_id,
                })
            else:
                passed.append(it)

        logger.info(
            "nli_gate_batch",
            batch=len(items),
            passed=len(passed),
            failed=len(invalid),
            total=self.total,
            failed_total=self.failed,
        )

        return passed, invalid