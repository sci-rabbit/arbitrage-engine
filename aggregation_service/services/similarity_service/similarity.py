from typing import Dict, Any

from core import Market
from core.similarity.entites.hf_gates import entity_match_score
from core.similarity.gates import hard_gate
from services.similarity_service.compute_scores import ComputeScores


class SimilarityService:
    def __init__(self, channels=None, weights=None):
        self.compute_scores = ComputeScores(
            channels=channels,
            weights=weights,
        )

    def get_similarity(
        self, a: Market, b: Market, threshold: float
    ) -> Dict[str, Any] | None:
        if not hard_gate(a, b):
            return None

        channel_scores = self.compute_scores.compute_channel_scores(a, b)
        if channel_scores is None:
            return None

        hf_score = entity_match_score(
            (a.normalized_title or "") + " " + (a.description or ""),
            (b.normalized_title or "") + " " + (b.description or ""),
        )

        # Final score
        final_score = self.compute_scores.compute_final_score(channel_scores, hf_score)

        if final_score < threshold:
            return None

        return {
            "final_score": round(final_score, 4),
            "channels": {k: round(v, 4) for k, v in channel_scores.items()},
            "hf_entity_score": round(hf_score, 3),
        }
