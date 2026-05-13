from dataclasses import dataclass

from core import Market


@dataclass
class PairItem:
    a: Market
    b: Market
    row: dict
    ce_score: float
    channel_scores: dict | None = None
    final_score: float | None = None
