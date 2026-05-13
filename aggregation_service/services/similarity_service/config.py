from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class SimilarityChannel:
    """
    Описание одного канала сравнения
    """
    name: str
    embedding_getter: Callable
    text_getter: Callable
    weight: float