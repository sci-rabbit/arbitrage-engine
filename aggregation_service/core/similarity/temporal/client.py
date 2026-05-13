from datetime import datetime

from core.similarity.temporal.parser import Interval, parse_temporal


def temporal_similarity(a: Interval, b: Interval) -> float:
    # приводим open-ended к «замкнутому» интервалу
    a_start, a_end = a
    b_start, b_end = b

    if a_end is None and a_start:
        # open-ended сверху → берем текущий день как конец
        a_end = datetime.today()
    if b_end is None and b_start:
        b_end = datetime.today()
    if a_end is None and not a_start:
        a_end = datetime.today()
    if b_end is None and not b_start:
        b_end = datetime.today()

    # теперь оба конца есть, сравниваем
    delta_days = abs((a_end.date() - b_end.date()).days)
    return 1.0 if delta_days <= 1 else 0.0


def get_temporal_similarity(a: str, b: str) -> dict:

    ia = parse_temporal(a)
    ib = parse_temporal(b)

    temp = temporal_similarity(ia, ib)

    return {
        "temporal": round(temp, 4),
        "interval_a": ia,
        "interval_b": ib,
    }
