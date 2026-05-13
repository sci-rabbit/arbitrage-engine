
import structlog

from core import Market
from core.similarity.entites.client import share_key_entities
from core.similarity.entites.hf_gates import entity_match_score, entity_match_scores
from core.similarity.numeric.client import get_numeric_result
from core.similarity.temporal.client import get_temporal_similarity

logger = structlog.getLogger(__name__)


def hard_gate(a: Market, b: Market) -> bool:
    text_a = a.normalized_title
    text_b = b.normalized_title

    # 1. Person disambiguation
    if entity_match_score(text_a, text_b) < 0.5:
        return False

    # 2. Entity anchors
    if not share_key_entities(a.normalized_title, b.normalized_title):
        return False

    # 3. Numeric contradiction
    numeric = get_numeric_result(a.normalized_title, b.normalized_title)
    if numeric["numeric_conflict"]:
        return False

    # 4. Temporal contradiction
    temporal = get_temporal_similarity(
        a.normalized_title,
        b.normalized_title,
    )
    if temporal["temporal"] == 0.0:
        return False

    # 4b. No date in titles — fall back to close_time (e.g. sports markets)
    ia, ib = temporal["interval_a"], temporal["interval_b"]
    if ia == (None, None) and ib == (None, None):
        if a.close_time and b.close_time:
            delta = abs((a.close_time.date() - b.close_time.date()).days)
            if delta > 1:
                return False

    return True


BATCH_SIZE = 200


def hard_gate_batch(
    pairs: list[tuple[Market, Market]],
) -> list[bool]:
    """
    Batched hard gate with per-batch and global logging.
    Preserves input order.
    """

    results: list[bool] = []

    total_pairs = len(pairs)
    total_passed = 0
    total_failed = 0

    logger.info(
        "hard_gate_batch_started",
        total_pairs=total_pairs,
        batch_size=BATCH_SIZE,
    )

    for batch_idx, i in enumerate(range(0, total_pairs, BATCH_SIZE), start=1):
        batch = pairs[i : i + BATCH_SIZE]

        batch_passed = 0
        batch_failed = 0

        # ---------- 1. entity_match_score (batched) ----------
        text_pairs = [
            (a.normalized_title or "", b.normalized_title or "") for a, b in batch
        ]

        entity_scores = entity_match_scores(text_pairs)

        # ---------- 2. remaining gates ----------
        for (a, b), ent_score in zip(batch, entity_scores):
            # 1. Person / entity disambiguation
            if ent_score < 0.5:
                results.append(False)
                batch_failed += 1
                continue

            # 2. Entity anchors
            if not share_key_entities(a.normalized_title, b.normalized_title):
                results.append(False)
                batch_failed += 1
                continue

            # 3. Numeric contradiction
            numeric = get_numeric_result(a.normalized_title, b.normalized_title)
            if numeric["numeric_conflict"]:
                results.append(False)
                batch_failed += 1
                continue

            # 4. Temporal contradiction
            temporal = get_temporal_similarity(a.normalized_title, b.normalized_title)
            if temporal["temporal"] == 0.0:
                results.append(False)
                batch_failed += 1
                continue

            # 4b. No date in titles — fall back to close_time (e.g. sports markets)
            ia, ib = temporal["interval_a"], temporal["interval_b"]
            if ia == (None, None) and ib == (None, None):
                if a.close_time and b.close_time:
                    delta = abs((a.close_time.date() - b.close_time.date()).days)
                    if delta > 1:
                        results.append(False)
                        batch_failed += 1
                        continue

            results.append(True)
            batch_passed += 1

        # ---------- batch log ----------
        total_passed += batch_passed
        total_failed += batch_failed

        logger.info(
            "hard_gate_batch_processed",
            batch_index=batch_idx,
            batch_size=len(batch),
            batch_passed=batch_passed,
            batch_failed=batch_failed,
            total_processed=total_passed + total_failed,
            total_passed=total_passed,
            total_failed=total_failed,
        )

    # ---------- final log ----------
    logger.info(
        "hard_gate_batch_finished",
        total_pairs=total_pairs,
        total_passed=total_passed,
        total_failed=total_failed,
        pass_rate=round(total_passed / total_pairs, 4) if total_pairs else 0.0,
    )

    return results


