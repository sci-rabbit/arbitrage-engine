from typing import Dict, Any, List


def format_predictfun_orderbook(
    api_response: Dict[str, Any],
) -> Dict[str, Dict[str, List]] | None:
    """
    Predict.fun orderbook normalizer.

    Expected API format:
    {
        "success": true,
        "data": {
            "marketId": number,
            "updateTimestampMs": number,
            "asks": [[price, size], ...],  // для Yes исхода
            "bids": [[price, size], ...]   // для Yes исхода
        }
    }

    The orderbook stores prices based on the `Yes` outcome.
    For `No` outcome: price_no = 1 - price_yes
    """
    
    if not api_response.get("success"):
        return None
    
    data = api_response.get("data", {})
    if not data:
        return None

    yes_bids_raw = data.get("bids", [])
    yes_asks_raw = data.get("asks", [])

    yes_bids = _normalize_bids(yes_bids_raw)
    yes_asks = _normalize_asks(yes_asks_raw)

    no_bids = _convert_asks_to_bids(yes_asks)
    no_asks = _convert_bids_to_asks(yes_bids)

    return {
        "yes": {"bids": yes_bids, "asks": yes_asks},
        "no": {"bids": no_bids, "asks": no_asks},
    }


def _normalize_bids(entries: Any) -> List[Dict[str, str]]:
    """
    Нормализует bids записи orderbook (сортировка от высокой цены к низкой).
    """
    if not entries:
        return []

    normalized: List[Dict[str, str]] = []
    for entry in entries:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            try:
                price = entry[0]
                qty = entry[1]
                normalized.append(
                    {
                        "price": str(price),
                        "size": str(qty),
                    }
                )
            except (TypeError, ValueError):
                continue

    return normalized


def _normalize_asks(entries: Any) -> List[Dict[str, str]]:
    """
    Нормализует asks записи orderbook (сортировка от низкой цены к высокой).
    """
    if not entries:
        return []

    normalized: List[Dict[str, str]] = []
    for entry in entries:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
            try:
                price = entry[0]
                qty = entry[1]
                normalized.append(
                    {
                        "price": str(price),
                        "size": str(qty),
                    }
                )
            except (TypeError, ValueError):
                continue

    return normalized


def _convert_bids_to_asks(
    bids: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """
    Конвертирует bids в asks: price_ask = 1 - price_bid
    Сортировка от низкой цены к высокой (best ask first).
    """
    asks: List[Dict[str, str]] = []
    for bid in bids:
        price_bid = float(bid["price"])
        price_ask = 1.0 - price_bid
        asks.append(
            {
                "price": f"{price_ask:.3f}",
                "size": bid["size"],
            }
        )

    return asks


def _convert_asks_to_bids(
    asks: List[Dict[str, str]],
) -> List[Dict[str, str]]:
    """
    Конвертирует asks в bids: price_bid = 1 - price_ask
    Сортировка от высокой цены к низкой (best bid first).
    """
    bids: List[Dict[str, str]] = []
    for ask in asks:
        price_ask = float(ask["price"])
        price_bid = 1.0 - price_ask
        bids.append(
            {
                "price": f"{price_bid:.3f}",
                "size": ask["size"],
            }
        )

    return bids

