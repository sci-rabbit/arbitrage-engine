from typing import Any


def format_kalshi_orderbook(
    api_response: dict[str, Any],
) -> dict[str, dict[str, list]] | None:
    """
    Kalshi orderbook normalizer.

    Expected API format:
    {
        "orderbook": {
            "yes": [[price_cents, size], ...],
            "no": [[price_cents, size], ...],
            "yes_dollars": [[price_str, size], ...],
            "no_dollars": [[price_str, size], ...]
        }
    }

    Only YES/NO in *cents* are used for trading logic.
    Asks are constructed:
        YES asks = 100 - NO bids
        NO asks  = 100 - YES bids
    """

    ob = api_response.get("orderbook", {})

    yes_bids = _normalize_book(ob.get("yes"))
    no_bids = _normalize_book(ob.get("no"))

    # Convert bids → asks (100 - price)
    yes_asks = _convert_bids_to_asks(no_bids)
    no_asks = _convert_bids_to_asks(yes_bids)

    return {
        "yes": {"bids": yes_bids, "asks": yes_asks},
        "no": {"bids": no_bids, "asks": no_asks},
    }


def _normalize_book(entries: Any) -> list[dict[str, str]]:
    if not entries:
        return []

    normalized = []
    for entry in entries:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            try:
                price = float(entry[0]) / 100  # ⬅️ ВАЖНО
                qty = float(entry[1])
                normalized.append(
                    {
                        "price": f"{price:.2f}",
                        "size": f"{qty:.0f}",
                    }
                )
            except (TypeError, ValueError):
                continue

    # best bid first
    normalized.sort(key=lambda x: -float(x["price"]))
    return normalized


def _convert_bids_to_asks(
    bids: list[dict[str, str]],
) -> list[dict[str, str]]:
    asks = []

    for bid in bids:
        price = 1.0 - float(bid["price"])  # ⬅️ ВАЖНО
        asks.append(
            {
                "price": f"{price:.2f}",
                "size": bid["size"],
            }
        )

    # lowest ask first
    asks.sort(key=lambda x: float(x["price"]))
    return asks
