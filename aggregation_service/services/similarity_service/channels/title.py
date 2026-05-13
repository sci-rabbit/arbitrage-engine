from core.similarity.numeric.client import get_numeric_result
from core.similarity.temporal.client import get_temporal_similarity
from services.similarity_service.channels.base import SimilarityChannel
from services.similarity_service.utils import cosine


class TitleChannel(SimilarityChannel):
    def __init__(self):
        self.name = "title"

    def score_batch(self, pairs):
        results = []

        for a, b in pairs:
            emb = cosine(a._embedding_np, b._embedding_np)

            numeric = get_numeric_result(
                a.normalized_title,
                b.normalized_title,
            )
            if numeric["numeric_conflict"]:
                results.append(0.0)
                continue

            temporal = get_temporal_similarity(
                a.normalized_title,
                b.normalized_title,
            )

            results.append(
                0.8 * emb
                + 0.1 * numeric["numeric_context_match"]
                + 0.1 * temporal["temporal"]
            )

        return results
