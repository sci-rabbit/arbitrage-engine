from core.similarity.numeric.client import get_numeric_result
from core.similarity.temporal.client import get_temporal_similarity
from services.similarity_service.channels.base import SimilarityChannel
from services.similarity_service.utils import cosine


class SemanticChannel(SimilarityChannel):
    def __init__(self):
        self.name = "semantic"

    def score_batch(self, pairs):
        results = []

        for a, b in pairs:
            emb = cosine(a._semantic_embedding_np, b._semantic_embedding_np)

            numeric = get_numeric_result(
                a.semantic_text,
                b.semantic_text,
            )
            if numeric["numeric_conflict"]:
                results.append(0.0)
                continue

            temporal = get_temporal_similarity(
                a.semantic_text,
                b.semantic_text,
            )

            results.append(
                0.6 * emb
                + 0.2 * numeric["numeric_context_match"]
                + 0.2 * temporal["temporal"]
            )

        return results
