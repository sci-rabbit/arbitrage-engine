"""Lazy initialization of NLI model for entailment detection."""
from typing import List, Tuple, Optional

import torch
import structlog
from transformers import pipeline

logger = structlog.getLogger(__name__)

_nli_model = None
device = 0 if torch.cuda.is_available() else -1

NLI_MODEL_NAME = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"

_nli_cache: dict[tuple[str, str], float] = {}


def get_nli_model():
    global _nli_model
    if _nli_model is None:
        logger.info("Loading NLI model", model=NLI_MODEL_NAME, device=device)
        _nli_model = pipeline(
            "text-classification",
            model=NLI_MODEL_NAME,
            device=device,
        )
        logger.info("NLI model loaded")
    return _nli_model


def entailment_scores_batch(
    pairs: List[Tuple[str, str]],
    batch_size: int = 32,
) -> List[float]:
    """
    For each (premise, hypothesis) pair returns probability that
    premise entails hypothesis.
    """
    if not pairs:
        return []

    results: List[Optional[float]] = [None] * len(pairs)
    uncached_indices: List[int] = []
    uncached_keys: List[Tuple[str, str]] = []

    for i, (p, h) in enumerate(pairs):
        key = (p[:512], h[:512])
        if key in _nli_cache:
            results[i] = _nli_cache[key]
        else:
            uncached_indices.append(i)
            uncached_keys.append(key)

    if uncached_keys:
        model = get_nli_model()
        inputs = [{"text": p, "text_pair": h} for p, h in uncached_keys]
        raw = model(inputs, batch_size=batch_size, top_k=None)

        for idx, key, result in zip(uncached_indices, uncached_keys, raw):
            ent_score = 0.0
            for item in result:
                if item["label"].lower() == "entailment":
                    ent_score = item["score"]
                    break
            _nli_cache[key] = ent_score
            results[idx] = ent_score

    return results