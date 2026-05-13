def aggregate(channel_scores: dict, weights: dict) -> float:
    return sum(
        channel_scores[name] * weights.get(name, 0.0)
        for name in channel_scores
    )
