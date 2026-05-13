from core.similarity.numeric.conflict import numeric_conflict
from core.similarity.numeric.pasrer import (
    numeric_context_match,
    parse_numeric_constraints,
)


def get_numeric_result(a_text: str, b_text: str):

    # ===== Numeric =====
    numeric_a = parse_numeric_constraints(a_text)
    numeric_b = parse_numeric_constraints(b_text)

    numeric_result = numeric_conflict(numeric_a, numeric_b)
    numeric_context_result = numeric_context_match(numeric_a, numeric_b)

    return {
        "numeric_conflict": numeric_result,
        "numeric_context_match": numeric_context_result,
        "numeric_a": numeric_a,
        "numeric_b": numeric_b,
    }


if __name__ == "__main__":

    class A:
        normalized_title: str = "Will annual inflation increase by 2.3% in March?"

    class B:
        normalized_title: str = "Will annual inflation increase by 3.2% in March?"

    print(get_numeric_result(B.normalized_title, A.normalized_title))
