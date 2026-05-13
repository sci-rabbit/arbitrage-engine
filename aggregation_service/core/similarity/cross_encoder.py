import asyncio
from typing import Iterable, Tuple, Optional

import numpy as np
import structlog
from sentence_transformers import CrossEncoder

logger = structlog.getLogger(__name__)

class CrossEncoderClient:
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        threshold: float = 0.85,
    ):
        self.model = CrossEncoder(model_name)
        self.threshold = threshold
        # Проверяем диапазон выходных значений модели
        # CrossEncoder ms-marco обычно возвращает значения, которые уже нужно нормализовать
        # Но проверим на реальных данных - если модель возвращает [0, 1], нормализация не нужна
        self._needs_normalization = True  # По умолчанию нормализуем

    def score_pair(self, a: str, b: str) -> float:
        score = self.model.predict([(a, b)])[0]
        return self._normalize(score) if self._needs_normalization else float(score)

    def score_batch(
        self,
        pairs: Iterable[Tuple[str, str]],
    ) -> list[float]:
        pairs_list = list(pairs)
        if not pairs_list:
            return []

        logger.info("Starting to score pairs", count=len(pairs_list))
        scores = self.model.predict(pairs_list)
        logger.info("Finished scoring pairs", count=len(pairs_list))

        if self._needs_normalization:
            return [self._normalize(float(s)) for s in scores]
        return [float(s) for s in scores]

    @staticmethod
    def _normalize(score: float) -> float:
        return float(1 / (1 + np.exp(-score)))



if __name__ == '__main__':
    client = CrossEncoderClient()
    print(client.score_pair("Will Marla Bhatia win the 2026 Valspar Championship?", "Will Akshay Bhatia win the Masters Tournament?"))