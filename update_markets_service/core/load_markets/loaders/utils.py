from typing import Optional, Dict, Any


def normalize_prices(m: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Возвращает нормализованные цены:
    yes_bid, yes_ask, no_bid, no_ask

    Kalshi: реальные bid/ask
    Polymarket: bid == ask == price
    """
    # Kalshi-like
    if "yes_bid" in m or "yes_ask" in m:
        return {
            "yes_bid": (
                float(m.get("yes_bid")) if m.get("yes_bid") is not None else None
            ),
            "yes_ask": (
                float(m.get("yes_ask")) if m.get("yes_ask") is not None else None
            ),
            "no_bid": float(m.get("no_bid")) if m.get("no_bid") is not None else None,
            "no_ask": float(m.get("no_ask")) if m.get("no_ask") is not None else None,
        }

    # Polymarket-like
    prices = m.get("outcomePrices")
    if prices and len(prices) == 2:
        yes = float(prices[0])
        no = float(prices[1])
        return {
            "yes_bid": yes,
            "yes_ask": yes,
            "no_bid": no,
            "no_ask": no,
        }

    return {
        "yes_bid": None,
        "yes_ask": None,
        "no_bid": None,
        "no_ask": None,
    }


def should_skip_market(m: Dict[str, Any]) -> bool:
    p = normalize_prices(m)

    yb, ya = p["yes_bid"], p["yes_ask"]
    nb, na = p["no_bid"], p["no_ask"]

    # 0. Вообще нет цен
    if any(v is None for v in (yb, ya, nb, na)):
        return True

    # 1. Вне [0, 1]
    for v in (yb, ya, nb, na):
        if v < 0 or v > 1:
            return True

    # 2. Полностью мёртвый рынок
    if yb == 0 and nb == 0:
        return True

    # 3. Вероятности не сходятся (для Poly это ГЛАВНОЕ)
    # Yes + No должно быть ≈ 1
    prob_sum = ya + na
    if not (0.97 <= prob_sum <= 1.03):
        return True

    # 4. Экстремальные значения → рынок почти resolved
    if yb >= 0.99 or nb >= 0.99:
        return True
    if ya <= 0.01 or na <= 0.01:
        return True

    # 5. Для Kalshi: битый стакан
    if yb > ya or nb > na:
        return True

    return False

# def should_skip_market(m: Dict[str, Any]) -> bool:
#     yes_bid = float(m.get("yes_bid") or 0)
#     yes_ask = float(m.get("yes_ask") or 100)
#     no_bid = float(m.get("no_bid") or 0)
#     no_ask = float(m.get("no_ask") or 100)
#
#     # 1. Полностью пустой маркет
#     if yes_bid == 0 and no_bid == 0:
#         return True
#
#     # 2. Нет ask-стороны (100 = никакие заявки не выставлены)
#     if yes_ask == 100 and no_ask == 100:
#         return True
#
#     # 3. Нет bid-стороны
#     if yes_bid == 0 and yes_ask == 100:
#         return True
#     if no_bid == 0 and no_ask == 100:
#         return True
#
#     # 4. Нереалистичные спреды (99–100, 0–1)
#     if abs(yes_ask - yes_bid) >= 98:   # например 1 vs 99 или 0 vs 100
#         return True
#     if abs(no_ask - no_bid) >= 98:
#         return True
#
#     # 5. Неконсистентность цен (арбитраж невозможен → рынок не торгуем)
#     # Пример: yes_bid=99 no_ask=1 (слишком близко к 100%)
#     if yes_bid >= 99 and no_ask <= 1:
#         return True
#     if no_bid >= 99 and yes_ask <= 1:
#         return True
#
#     # 6. Цена обеих сторон равна (стакан сломан)
#     if yes_bid >= yes_ask:
#         return True
#     if no_bid >= no_ask:
#         return True

# Если маркет нормальный – не фильтруем
#   return False
