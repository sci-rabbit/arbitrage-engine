import re
from typing import List, Optional
from .models import NumericConstraint, Operator

# # ====== Конфигурация ======
# COMPARATORS = {
#     ">=": Operator.GTE,
#     "at least": Operator.GTE,
#     "over": Operator.GT,
#     "above": Operator.GT,
#     ">": Operator.GT,
#     "<=": Operator.LTE,
#     "at most": Operator.LTE,
#     "under": Operator.LT,
#     "below": Operator.LT,
#     "<": Operator.LT,
#     "equals": Operator.EQ,
#     "exactly": Operator.EQ,
# }

NUMBER_RE = r"(?P<num>\d{1,3}(?:[,\d]*)(?:\.\d+)?)\s*(?P<suffix>k|m|%|)?"
MULTIPLIERS = {"k": 1_000, "m": 1_000_000, "%": 1, None: 1}


# (low)/(high) and word-bounded low/high for "hit (LOW) $80" / "hit (HIGH) $130"
NUMERIC_VERBS = r"(above|over|greater than|at least|>=|surpasses|reaches|below|under|less than|<=|falls under|at most|equals|exactly|=|\(low\)|\(high\)|(?<!\w)(?:low|high)(?!\w))"


def verb_to_operator(verb: str) -> Operator:
    verb = verb.lower()
    if verb in ["above", "over", "greater than", ">=", "surpasses", "reaches", "at least", "(high)", "high"]:
        return Operator.GTE
    if verb in ["below", "under", "less than", "<=", "falls under", "at most", "(low)", "low"]:
        return Operator.LTE
    if verb in ["equals", "exactly", "="]:
        return Operator.EQ
    # fallback
    return Operator.EQ


def parse_number(value: str, suffix: Optional[str]) -> float:
    return float(value.replace(",", "")) * MULTIPLIERS.get(suffix, 1)


def parse_numeric_constraints(text: str) -> List[NumericConstraint]:
    text = text.lower()
    constraints: List[NumericConstraint] = []
    covered_spans: List[tuple[int, int]] = []

    pattern = rf"{NUMERIC_VERBS}\s*\$?{NUMBER_RE}"
    for match in re.finditer(pattern, text):
        verb = match.group(1)
        op = verb_to_operator(verb)
        value = parse_number(match.group("num"), match.group("suffix"))

        # берем 5 слов до числа как span
        tokens = re.findall(r"\b\w+\b", text)
        idx = len(re.findall(r"\b\w+\b", text[: match.start()]))
        span_text = " ".join(tokens[max(0, idx - 5) : idx])

        constraints.append(
            NumericConstraint(value=value, operator=op, span_text=span_text)
        )

        covered_spans.append(match.span())

    # Второй проход: «голые» числа без явного глагола (EQ по умолчанию).
    number_pattern = rf"\$?{NUMBER_RE}"
    tokens = re.findall(r"\b\w+\b", text)
    for match in re.finditer(number_pattern, text):
        start, end = match.span()
        # пропускаем, если это число уже попало в шаблон с глаголом
        if any(not (end <= s or start >= e) for s, e in covered_spans):
            continue

        value = parse_number(match.group("num"), match.group("suffix"))

        idx = len(re.findall(r"\b\w+\b", text[: start]))
        span_text = " ".join(tokens[max(0, idx - 5) : idx])

        constraints.append(
            NumericConstraint(
                value=value,
                operator=Operator.EQ,
                span_text=span_text,
            )
        )

    return constraints


def numeric_context_match(
    a: List[NumericConstraint], b: List[NumericConstraint], tolerance: float = 0.0
) -> bool:
    for ca in a:
        for cb in b:
            max_val = max(ca.value, cb.value)
            if max_val == 0:
                continue  # или пропустить, или сравнивать особым образом
            # Above / Greater than
            if ca.operator in (Operator.GT, Operator.GTE) and cb.operator in (
                Operator.GT,
                Operator.GTE,
            ):
                if abs(ca.value - cb.value) / max_val <= tolerance:
                    return True
            # Below / Less than
            elif ca.operator in (Operator.LT, Operator.LTE) and cb.operator in (
                Operator.LT,
                Operator.LTE,
            ):
                if abs(ca.value - cb.value) / max_val <= tolerance:
                    return True
            # Exact
            elif ca.operator == Operator.EQ and cb.operator == Operator.EQ:
                if ca.value == cb.value:
                    return True
    return False
