import re
from datetime import datetime, timedelta

import dateparser
from dateparser.search import search_dates

Interval = tuple[datetime | None, datetime | None]

MIN_YEAR = 2026
MAX_YEAR = 3000


def safe_year(y: int) -> bool:
    return MIN_YEAR <= y <= MAX_YEAR


def year_interval(year: int) -> Interval:
    if not safe_year(year):
        return None, None
    return (
        datetime(year, 1, 1),
        datetime(year, 12, 31, 23, 59, 59),
    )


def parse_temporal(expr: str) -> Interval:
    """
    Находит временную привязку ТОЛЬКО для событий.
    Numeric thresholds / FX / odds сюда не проходят.
    """
    text = expr.lower()

    # ❌ hard-stop: numeric / price-like markets
    if re.search(r"\b\d+\.\d{2,}\b", text):  # 7.9999, 1500.00
        return None, None

    # 1. "in YYYY"
    m = re.search(r"\bin\s+(\d{4})\b", text)
    if m:
        y = int(m.group(1))
        if safe_year(y):
            return year_interval(y)

    # 2. "before <month year>"
    m = re.search(r"\bbefore\s+([a-z]+\s+\d{4})\b", text)
    if m:
        d = dateparser.parse(m.group(1))
        if d and safe_year(d.year):
            return None, datetime(d.year, d.month, 1)

    # 3. "after <month year>"
    m = re.search(r"\bafter\s+([a-z]+\s+\d{4})\b", text)
    if m:
        d = dateparser.parse(m.group(1))
        if d and safe_year(d.year):
            return datetime(d.year, d.month, 1), None

    # 4. "by <month year>"
    m = re.search(r"\bby\s+([a-z]+\s+\d{4})\b", text)
    if m:
        d = dateparser.parse(m.group(1))
        if d and safe_year(d.year):
            if d.month == 12:
                last_day = 31
            else:
                next_month = datetime(d.year, d.month + 1, 1)
                last_day = (next_month - timedelta(days=1)).day
            return None, datetime(d.year, d.month, last_day, 23, 59, 59)

    # 5. fallback — но С ФИЛЬТРОМ
    res = search_dates(text)
    if not res:
        return None, None

    for _, dt in res:
        if not safe_year(dt.year):
            continue
        try:
            return dt, dt + timedelta(days=1)
        except OverflowError:
            continue

    return None, None
