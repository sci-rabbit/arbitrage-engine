from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CreateSubDTO:
    subscription_name: str
    price: Decimal
    duration_days: int

@dataclass
class UpdateSubDTO:
    subscription_name: str | None = None
    price: Decimal | None = None
    duration_days: int | None = None
