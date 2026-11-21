"""Rounding helpers used by the Income-tax Act."""


def round_to_10(amount: int) -> int:
    """Round to the nearest ten rupees, halves away from zero (s.288B)."""
    sign = -1 if amount < 0 else 1
    return sign * ((abs(amount) + 5) // 10 * 10)


def round_down_to_100(amount: int) -> int:
    """Interest is charged on the amount with any fraction of 100 ignored."""
    return amount // 100 * 100
