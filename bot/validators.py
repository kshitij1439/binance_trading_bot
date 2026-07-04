"""
Input validation for the trading bot CLI.

All functions raise `ValidationError` (a subclass of ValueError) on bad
input so the CLI layer can catch a single, predictable exception type.
"""

import re
from typing import Optional, Union

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}
# Basic sanity check: 3-20 uppercase letters/digits, e.g. BTCUSDT, ETHUSDT
SYMBOL_RE = re.compile(r"^[A-Z0-9]{5,20}$")


class ValidationError(ValueError):
    """Raised when CLI input fails validation."""


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected format like 'BTCUSDT' (5-20 alphanumeric chars)."
        )
    return symbol


def validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity: float) -> float:
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if quantity <= 0:
        raise ValidationError(f"Quantity must be > 0, got {quantity}.")
    return quantity


def validate_price(price: Optional[Union[str, float]], order_type: str) -> Optional[float]:
    """
    Price is required for LIMIT and STOP_LIMIT orders, must be None/omitted
    for MARKET orders.
    """
    if order_type == "MARKET":
        if price is not None:
            raise ValidationError("Price must not be provided for MARKET orders.")
        return None

    # LIMIT / STOP_LIMIT
    if price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    try:
        price = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if price <= 0:
        raise ValidationError(f"Price must be > 0, got {price}.")
    return price


def validate_stop_price(
    stop_price: Optional[Union[str, float]], order_type: str
) -> Optional[float]:
    """Stop price is required only for STOP_LIMIT orders."""
    if order_type != "STOP_LIMIT":
        return None
    if stop_price is None:
        raise ValidationError("stop_price is required for STOP_LIMIT orders.")
    try:
        stop_price = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"stop_price must be a number, got '{stop_price}'.")
    if stop_price <= 0:
        raise ValidationError(f"stop_price must be > 0, got {stop_price}.")
    return stop_price
