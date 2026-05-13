# models.py
from dataclasses import dataclass
from enum import Enum


class Operator(str, Enum):
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    EQ = "=="


@dataclass
class NumericConstraint:
    value: float
    operator: Operator
    span_text: str
