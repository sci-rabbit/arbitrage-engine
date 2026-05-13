from typing import Optional, Dict

import structlog

from services.similarity_service.aggregation.weighted_sum import aggregate

logger = structlog.getLogger(__name__)


class ComputeScores:
    def __init__(self, channels=None, weights=None):
        self.channels = channels or []
        self.weights = weights or {"title": 0.7, "semantic": 0.3}

    def compute_channel_scores_batch(self, pairs):
        """
        Returns:
        List[Dict[channel_name, score]] aligned with pairs
        """
        scores_per_channel = {}

        for ch in self.channels:
            scores_per_channel[ch.name] = ch.score_batch(pairs)

        results = []
        for i in range(len(pairs)):
            row = {
                name: scores[i]
                for name, scores in scores_per_channel.items()
            }
            if all(v == 0.0 for v in row.values()):
                results.append(None)
            else:
                results.append(row)

        return results

    def compute_final_scores_batch(self, channel_scores_batch):
        final_scores = []

        for channel_scores in channel_scores_batch:
            if channel_scores is None:
                final_scores.append(0.0)
            else:
                final_scores.append(
                    aggregate(channel_scores, self.weights)
                )

        return final_scores
