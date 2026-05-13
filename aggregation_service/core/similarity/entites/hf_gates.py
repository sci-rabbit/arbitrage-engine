# core/similarity/entities/hf_gate.py

import re
from typing import List, Tuple

import structlog
from rapidfuzz import fuzz

from core.similarity.ner_client import get_ner_model

logger = structlog.getLogger(__name__)

CRITICAL_ENTITIES = {
    "PER",
    "ORG",
    "LOC",
    "EVENT",
    "PRODUCT",
    "MISC",
}

# Process-level NER cache: normalized_title -> list of (entity, label) tuples
_ner_cache: dict[str, List[Tuple[str, str]]] = {}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _parse_ner_doc(doc) -> List[Tuple[str, str]]:
    return list(
        {
            (normalize_text(ent["word"]), ent["entity_group"])
            for ent in doc
            if ent["entity_group"] in CRITICAL_ENTITIES and ent["score"] >= 0.85
        }
    )


def extract_entities_hf(text: str) -> List[Tuple[str, str]]:
    key = (text or "")[:1000]
    if key in _ner_cache:
        return _ner_cache[key]
    ner = get_ner_model()
    result = ner(key)
    ents = _parse_ner_doc(result)
    _ner_cache[key] = ents
    return ents


def extract_entities_hf_batch(texts: List[str]) -> List[List[Tuple[str, str]]]:
    keys = [(t or "")[:1000] for t in texts]

    # Collect unique texts not yet in cache
    missing_keys = list(dict.fromkeys(k for k in keys if k not in _ner_cache))

    if missing_keys:
        ner = get_ner_model()
        raw_results = ner(missing_keys, batch_size=32)
        for key, doc in zip(missing_keys, raw_results):
            _ner_cache[key] = _parse_ner_doc(doc)

    return [_ner_cache[k] for k in keys]


def entity_match_score(text1: str, text2: str) -> float:
    ents1, ents2 = extract_entities_hf_batch([text1, text2])
    logger.debug("entity_match_score", ents1=ents1, ents2=ents2)
    if (ents1 and not ents2) or (not ents1 and ents2):
        return 0.0

    if not ents1 and not ents2:
        return 0.5

    orgs1 = [(e, l) for (e, l) in ents1 if l == "ORG"]
    orgs2 = [(e, l) for (e, l) in ents2 if l == "ORG"]
    if orgs1 or orgs2:
        has_org_match = False
        for e1, _ in orgs1:
            for e2, _ in orgs2:
                if fuzz.token_set_ratio(e1, e2) >= 75:
                    has_org_match = True
                    break
            if has_org_match:
                break
        if not has_org_match:
            return 0.0

    matched = 0
    for e1, l1 in ents1:
        if any(l1 == l2 and fuzz.token_set_ratio(e1, e2) >= 75 for e2, l2 in ents2):
            matched += 1

    return matched / max(len(ents1), len(ents2))


def entity_match_scores(
    text_pairs: List[Tuple[str, str]],
) -> List[float]:
    flat_texts: List[str] = []
    for t1, t2 in text_pairs:
        flat_texts.append((t1 or "")[:1000])
        flat_texts.append((t2 or "")[:1000])

    flat_entities = extract_entities_hf_batch(flat_texts)

    scores: List[float] = []

    for i in range(0, len(flat_entities), 2):
        ents1 = flat_entities[i]
        ents2 = flat_entities[i + 1]

        if (ents1 and not ents2) or (not ents1 and ents2):
            scores.append(0.0)
            continue

        if not ents1 and not ents2:
            scores.append(0.5)
            continue

        orgs1 = [(e, l) for (e, l) in ents1 if l == "ORG"]
        orgs2 = [(e, l) for (e, l) in ents2 if l == "ORG"]
        if orgs1 or orgs2:
            has_org_match = False
            for e1, _ in orgs1:
                for e2, _ in orgs2:
                    if fuzz.token_set_ratio(e1, e2) >= 75:
                        has_org_match = True
                        break
                if has_org_match:
                    break
            if not has_org_match:
                scores.append(0.0)
                continue

        matched = 0
        for e1, l1 in ents1:
            if any(l1 == l2 and fuzz.token_set_ratio(e1, e2) >= 75 for e2, l2 in ents2):
                matched += 1

        scores.append(matched / max(len(ents1), len(ents2)))

    return scores


if __name__ == "__main__":
    a_text = "Will Akshay Bhatia win the Masters Tournament?"
    b_text = "Will Akshay Bhatia win the 2026 Valspar Championship?"
    print(entity_match_score(a_text, b_text))