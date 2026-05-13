from core.similarity.numeric.conflict import numeric_conflict
from core.similarity.numeric.pasrer import (
    parse_numeric_constraints,
    numeric_context_match,
)
from core.similarity.temporal.client import get_temporal_similarity


def numeric_temporal_match(a_text: str, b_text: str) -> dict:
    """
    Высокоуровневая проверка совпадения двух текстов по numeric + temporal
    """
    # ===== Numeric =====
    numeric_a = parse_numeric_constraints(a_text)
    numeric_b = parse_numeric_constraints(b_text)
    numeric_result = numeric_conflict(numeric_a, numeric_b)

    # ===== Temporal =====
    temporal_result = get_temporal_similarity(a_text, b_text)

    numeric_context_result =  numeric_context_match(numeric_a, numeric_b)

    return {
        "numeric_conflict": numeric_result,
        "numeric_context_match": numeric_context_result,
        "temporal_similarity": temporal_result,
        "numeric_a": numeric_a,
        "numeric_b": numeric_b,
    }

if __name__ == "__main__":
    a_text = "Will the spot price of Solana be above $150.00 before Jan 1, 2027?"
    b_text = "Will the price of Solana be above $150 in 2026?"
    res = numeric_temporal_match(a_text, b_text)
    print(res)
