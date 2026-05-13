"""
Утилита для генерации URL маркетов на оригинальных платформах.
"""


def generate_market_url(
    platform: str, 
    platform_market_id: str, 
    event_slug: str | None = None,
    event_id: str | None = None,
    series_ticker: str | None = None
) -> str:
    """
    Генерирует URL для маркета на оригинальной платформе.
    
    Args:
        platform: Название платформы (kalshi, polymarket, predict_fun)
        platform_market_id: ID маркета на платформе
        event_slug: Slug события (используется для polymarket и predict_fun)
        event_id: ID события (используется для kalshi как event_ticker)
        series_ticker: Series ticker для Kalshi (получается из API /events/{event_ticker})
    
    Returns:
        URL маркета на оригинальной платформе
    """
    if platform == "polymarket":
        # Polymarket использует event_slug для URL, если доступен
        if event_slug:
            return f"https://polymarket.com/event/{event_slug}"
        # Fallback на market ID, если slug недоступен
        return f"https://polymarket.com/market/{platform_market_id}"
    
    elif platform == "kalshi":
        # Kalshi использует series_ticker и market_ticker для URL
        # Формат: https://kalshi.com/markets/{series_ticker}/{market_ticker}
        if series_ticker and event_id:
            return f"https://kalshi.com/markets/{series_ticker.lower()}/{event_id.lower()}"
        # Fallback на event_ticker, если series_ticker недоступен
        if series_ticker and platform_market_id:
            return f"https://kalshi.com/markets/{series_ticker.lower()}/{platform_market_id.lower()}"
        # Fallback, если ничего не доступно
        return f"https://kalshi.com/trade/{platform_market_id.lower()}"
    
    elif platform == "predict_fun":
        # Predict.fun использует event_slug для URL
        if event_slug:
            return f"https://predict.fun/market/{event_slug}"
        # Fallback на market ID, если slug недоступен
        return f"https://predict.fun/market/{platform_market_id}"
    
    else:
        # Fallback для неизвестных платформ
        return "#"

