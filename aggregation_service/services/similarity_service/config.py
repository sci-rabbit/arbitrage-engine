from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SimilarityChannel:
    """
    Описание одного канала сравнения
    """
    name: str
    embedding_getter: Callable
    text_getter: Callable
    weight: float
