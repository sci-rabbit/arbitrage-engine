from typing import Any


def get_float(volume: Any):
    try:
        return float(volume)
    except (TypeError, ValueError):
        return 0
