from core import Market


def build_semantic_text(market: Market) -> str:
    parts = []

    if market.title:
        parts.append(market.title)

    if market.description:
        parts.append(market.description)

    raw = market.raw or {}

    # Kalshi
    if "rules_primary" in raw:
        parts.append(raw["rules_primary"])
    if "rules_secondary" in raw:
        parts.append(raw["rules_secondary"])

    # Polymarket — часто rules лежат в description внутри events
    events = raw.get("events") or []
    if isinstance(events, list) and events:
        first = events[0] or {}
        desc = first.get("description")
        if desc:
            parts.append(desc)

    return "\n".join(parts)
