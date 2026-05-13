from typing import List, Dict, Any, Optional
import structlog

logger = structlog.getLogger(__name__)

# Константы для арбитража
MIN_MAX_SPREAD = 0.03  # Минимальный максимальный спред для валидации


def normalize_asks(asks: List[Any]) -> List[Dict[str, float]]:
    out = []

    for level in asks:
        if isinstance(level, dict):
            out.append(
                {
                    "price": float(level["price"]),
                    "size": float(level["size"]),
                }
            )
        elif isinstance(level, list):
            out.append(
                {
                    "price": float(level[0]),
                    "size": float(level[1]),
                }
            )
        else:
            logger.warning(
                "unknown_ask_format",
                level=level,
                level_type=type(level).__name__,
            )

    return sorted(out, key=lambda x: x["price"])


def cheapest_ask(
    asks: List[Any],
    min_size: float,
) -> Optional[Dict[str, float]]:
    for level in normalize_asks(asks):
        if level["size"] >= min_size:
            return level
    return None


def calc_depth_arbitrage(
    asks1: List[Any],
    asks2: List[Any],
    price_threshold: float,
) -> Optional[Dict[str, Any]]:
    a1 = normalize_asks(asks1)
    a2 = normalize_asks(asks2)

    if not a1 or not a2:
        return None

    min_price_a1 = min(l["price"] for l in a1)
    min_price_a2 = min(l["price"] for l in a2)

    size_at_min_price_a1 = sum(l["size"] for l in a1 if l["price"] == min_price_a1)
    size_at_min_price_a2 = sum(l["size"] for l in a2 if l["price"] == min_price_a2)

    size_at_max_spread = min(size_at_min_price_a1, size_at_min_price_a2)

    raw_max_spread = 1 - (min_price_a1 + min_price_a2)
    max_spread = max(MIN_MAX_SPREAD, raw_max_spread)

    avg_sum_at_max_spread = 1 - max_spread
    pnl_at_max_spread = size_at_max_spread * max_spread

    i = j = 0
    total_size = 0.0
    total_cost = 0.0

    min_spread = float("inf")
    avg_sum_at_min_spread = None
    pnl_at_min_spread = None

    while i < len(a1) and j < len(a2):
        p1, s1 = a1[i]["price"], a1[i]["size"]
        p2, s2 = a2[j]["price"], a2[j]["size"]

        price_sum = p1 + p2
        if price_sum > price_threshold:
            break

        take = min(s1, s2)

        total_size += take
        total_cost += take * price_sum

        spread = 1 - price_sum

        if spread < min_spread:
            min_spread = spread
            avg_sum_at_min_spread = total_cost / total_size
            pnl_at_min_spread = total_size - total_cost

        a1[i]["size"] -= take
        a2[j]["size"] -= take

        if a1[i]["size"] <= 0:
            i += 1
        if a2[j]["size"] <= 0:
            j += 1

    if total_size <= 0:
        return None

    final_avg_price = total_cost / total_size
    final_spread = 1 - final_avg_price
    final_pnl = total_size - total_cost

    return {
        "max_spread": max_spread,
        "avg_sum_at_max_spread": avg_sum_at_max_spread,
        "pnl_at_max_spread": pnl_at_max_spread,
        "size_at_max_spread": size_at_max_spread,
        "min_spread": min_spread,
        "avg_sum_at_min_spread": avg_sum_at_min_spread,
        "pnl_at_min_spread": pnl_at_min_spread,
        "final_contracts": total_size,
        "final_cost": total_cost,
        "final_avg_price": final_avg_price,
        "final_spread": final_spread,
        "final_pnl": final_pnl,
    }


def check_arbitrage(
    ob1: Dict[str, Any],
    ob2: Dict[str, Any],
    min_size: float = 25,
    price_threshold: float = 0.97,
) -> List[Dict[str, Any]]:
    results = []

    # Валидация структуры orderbook
    for ob, ob_name in [(ob1, "ob1"), (ob2, "ob2")]:
        if not isinstance(ob, dict):
            logger.warning("invalid_orderbook_type", orderbook=ob_name, type=type(ob).__name__)
            return []
        for side in ["yes", "no"]:
            if side not in ob:
                logger.warning("missing_side_in_orderbook", orderbook=ob_name, side=side)
                return []
            if not isinstance(ob[side], dict) or "asks" not in ob[side]:
                logger.warning(
                    "invalid_orderbook_structure",
                    orderbook=ob_name,
                    side=side,
                    has_asks="asks" in ob[side] if isinstance(ob[side], dict) else False,
                )
                return []

    for side1, side2 in (("yes", "no"), ("no", "yes")):
        ask1 = cheapest_ask(ob1[side1]["asks"], min_size)
        ask2 = cheapest_ask(ob2[side2]["asks"], min_size)

        if not ask1 or not ask2:
            continue

        first_sum = ask1["price"] + ask2["price"]
        if first_sum >= price_threshold:
            continue

        depth = calc_depth_arbitrage(
            ob1[side1]["asks"],
            ob2[side2]["asks"],
            price_threshold,
        )

        if not depth or depth["final_pnl"] <= 0:
            continue

        results.append(
            {
                "direction": f"{side1.upper()} + {side2.upper()}",
                "entry_price_1": ask1["price"],
                "entry_price_2": ask2["price"],
                "entry_spread": 1 - first_sum,
                "min_size_per_market": min(ask1["size"], ask2["size"]),
                **depth,
            }
        )

    results.sort(key=lambda x: x["final_pnl"], reverse=True)
    return results
