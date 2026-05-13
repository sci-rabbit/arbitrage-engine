import structlog

from core.similarity.gates import hard_gate_batch
from services.similarity_service.stages.dataclass import PairItem

logger = structlog.getLogger(__name__)


class HardGateStage:
    name = "hard_gate"

    def __init__(self, batch_size=200):
        self.batch_size = batch_size
        self.total = 0
        self.failed = 0

    def process_batch(self, items: list[PairItem]):
        pairs = [(it.a, it.b) for it in items]

        mask = hard_gate_batch(pairs)

        passed = []
        invalid = []

        for it, ok in zip(items, mask):
            self.total += 1
            if not ok:
                self.failed += 1
                invalid.append(
                    {
                        "a_market_id": it.a.platform_market_id,
                        "b_market_id": it.b.platform_market_id,
                    }
                )
            else:
                passed.append(it)

        logger.info(
            "hard_gate_batch",
            batch=len(items),
            passed=len(passed),
            failed=len(invalid),
            total=self.total,
            failed_total=self.failed,
        )

        return passed, invalid
