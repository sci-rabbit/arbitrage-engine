from dataclasses import dataclass
from decimal import Decimal


@dataclass
class DepositDTO:
    amount: Decimal
    description: str | None = None


@dataclass
class WithdrawDTO:
    amount: Decimal
    description: str | None = None
