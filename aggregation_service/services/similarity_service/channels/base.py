class SimilarityChannel:
    name: str

    def score(self, a, b) -> float:
        raise NotImplementedError

    def score_batch(self, pairs):
        """
        Default fallback — per-pair.
        Каналы могут переопределять.
        """
        return [self.score(a, b) for a, b in pairs]
