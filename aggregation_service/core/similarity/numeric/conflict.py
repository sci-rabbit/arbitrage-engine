# conflict.py
from typing import List
from .models import NumericConstraint, Operator


def _looks_like_year(v: float) -> bool:
    return 2020 <= v <= 2035


def operators_conflict(a: NumericConstraint, b: NumericConstraint, tolerance: float = 0.0) -> bool:
    """
    True если значения a и b логически противоречат.

    Конфликт возникает если:
    1. Противоположные операторы (>= vs <=) - проверяем логическую несовместимость
    2. Оба EQ но разные значения
    3. Оба одного типа (>= vs >=), но значения сильно различаются (больше чем tolerance)
    """
    # Противоположные операторы
    if a.operator in (Operator.GT, Operator.GTE) and b.operator in (Operator.LT, Operator.LTE):
        return a.value >= b.value
    if a.operator in (Operator.LT, Operator.LTE) and b.operator in (Operator.GT, Operator.GTE):
        return b.value >= a.value

    # Оба EQ - конфликт если значения разные
    if a.operator == Operator.EQ and b.operator == Operator.EQ:
        # Год (2020-2035) и не-год — разные семантические типы, не конфликт
        if _looks_like_year(a.value) != _looks_like_year(b.value):
            return False
        return a.value != b.value
    
    # Если оба оператора одного типа, проверяем на значительное расхождение
    # (например, "above 100k" vs "above 150k" - слишком разные пороги)
    if a.operator == b.operator:
        max_val = max(abs(a.value), abs(b.value))
        if max_val > 0:
            relative_diff = abs(a.value - b.value) / max_val
            # Если разница больше tolerance (по умолчанию 5%), считаем конфликтом
            # Но только если это не близкие значения (например, 100k vs 105k - ок, но 100k vs 150k - конфликт)
            if relative_diff > tolerance:
                return True
    
    return False


def numeric_conflict(a: List[NumericConstraint], b: List[NumericConstraint]) -> bool:
    """
    Проверяет, есть ли хотя бы один конфликт между двумя списками числовых ограничений
    """
    for ca in a:
        for cb in b:
            if operators_conflict(ca, cb):
                return True
    return False
