"""Lazy initialization of NER model to avoid loading on import."""

from __future__ import annotations

import torch
from transformers import pipeline

_ner_model: pipeline | None = None

device = 0 if torch.cuda.is_available() else -1

def get_ner_model():
    """Lazy initialization of NER pipeline."""
    global _ner_model
    if _ner_model is None:
        _ner_model = pipeline(
            "ner",
            model="Babelscape/wikineural-multilingual-ner",
            aggregation_strategy="simple",
            device=device,
        )
    return _ner_model

# import re
# from concurrent.futures import ProcessPoolExecutor, as_completed
# from transformers import pipeline
#
# CRITICAL_ENTITIES = {"PER", "ORG", "LOC"}
#
# # --- глобальная функция для одного батча ---
# def process_batch(batch):
#     ner = pipeline(
#         "ner",
#         model="dbmdz/bert-large-cased-finetuned-conll03-english",
#         aggregation_strategy="simple",
#         device=-1,  # CPU
#     )
#     def normalize_text(text: str) -> str:
#         return re.sub(r"\s+", " ", text).strip().lower()
#
#     batch_results = ner(batch)
#     return [
#         [
#             (normalize_text(ent["word"]), ent["entity_group"])
#             for ent in doc
#             if ent["entity_group"] in CRITICAL_ENTITIES and ent["score"] >= 0.85
#         ]
#         for doc in batch_results
#     ]
#
# # --- главная функция ---
# def extract_entities_hf_batch_parallel(texts: list[str], batch_size=32, max_workers=6):
#     all_results = []
#     batches = [texts[i:i+batch_size] for i in range(0, len(texts), batch_size)]
#
#     with ProcessPoolExecutor(max_workers=max_workers) as executor:
#         futures = [executor.submit(process_batch, batch) for batch in batches]
#         for future in as_completed(futures):
#             all_results.extend(future.result())
#
#     return all_results






# Пример вызова
# if __name__ == "__main__":
#
#     import time
#
#     # Тестовый текст
#     test_text = "Apple was founded by Steve Jobs in California."
#
#     def test_ner_batch(n: int):
#         # Создаём батч из n одинаковых текстов
#         batch = [test_text] * n
#
#         start = time.time()
#         results = extract_entities_hf_batch_parallel(batch, batch_size=200)  # размер подбатча можно менять
#         end = time.time()
#
#         print(f"Processed {n} texts in {end - start:.2f} seconds")
#         for i, ents in enumerate(results[:5]):  # показываем первые 5 результатов
#             print(f"Text {i+1}: {ents}")
#
#     test_ner_batch(10000)   # проверяем на 20 текстах
