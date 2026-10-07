from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


MONEY_PLACES = Decimal("0.01")
QUANTITY_PLACES = Decimal("0.000001")


def to_money(value: Decimal | int | float | str | None) -> Decimal:
    if value is None:
        return Decimal("0.00")

    return Decimal(str(value)).quantize(
        MONEY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def to_quantity(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(
        QUANTITY_PLACES,
        rounding=ROUND_HALF_UP,
    )


def percentage_of(
    amount: Decimal,
    percentage: Decimal,
) -> Decimal:
    amount = to_money(amount)
    percentage = to_money(percentage)

    return to_money(
        amount * percentage / Decimal("100")
    )


def safe_subtract(
    first: Decimal,
    second: Decimal,
) -> Decimal:
    result = to_money(first) - to_money(second)

    if result < 0:
        return Decimal("0.00")

    return to_money(result)


def calculate_change(
    received: Decimal,
    required: Decimal,
) -> Decimal:
    received = to_money(received)
    required = to_money(required)

    if received <= required:
        return Decimal("0.00")

    return to_money(received - required)
