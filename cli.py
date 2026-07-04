#!/usr/bin/env python3
"""
CLI entry point for the Simplified Trading Bot (Binance Futures Testnet).

Examples
--------
Market order:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order:
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

Stop-Limit order (bonus):
    python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT \\
        --quantity 0.01 --price 60000 --stop-price 60500

Interactive mode (bonus — guided prompts with step-by-step validation):
    python cli.py --interactive
    python cli.py -i
    python cli.py            # no args at all also triggers interactive mode

API credentials are read from environment variables BINANCE_API_KEY /
BINANCE_API_SECRET (a .env file is supported via python-dotenv), or can be
passed explicitly with --api-key / --api-secret.
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceAPIError, BinanceFuturesTestnetClient, NetworkError, DEFAULT_BASE_URL
from bot.logging_config import get_logger
from bot.orders import OrderManager, OrderRequest
from bot.utils import safe_print
from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

logger = get_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Place Market / Limit / Stop-Limit orders on Binance Futures Testnet (USDT-M).",
    )
    # None of the order fields are `required=True` at the argparse level.
    # That's deliberate: running with zero arguments (or --interactive) drops
    # into the guided prompt flow instead of argparse hard-erroring before we
    # get a chance to check which mode the user wants. Non-interactive mode
    # re-validates that all required fields were actually supplied (see
    # `run_non_interactive`) and reports missing ones the same way invalid
    # ones are reported.
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Run in guided interactive prompt mode"
    )
    parser.add_argument("--symbol", default=None, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", default=None, choices=["BUY", "SELL", "buy", "sell"])
    parser.add_argument(
        "--type",
        dest="order_type",
        default=None,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
    )
    parser.add_argument("--quantity", type=float, default=None, help="Order quantity")
    parser.add_argument("--price", type=float, default=None, help="Required for LIMIT / STOP_LIMIT")
    parser.add_argument(
        "--stop-price", type=float, default=None, help="Required for STOP_LIMIT only"
    )
    parser.add_argument(
        "--time-in-force",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time in force for LIMIT / STOP_LIMIT orders (default: GTC)",
    )
    parser.add_argument("--api-key", default=None, help="Overrides BINANCE_API_KEY env var")
    parser.add_argument("--api-secret", default=None, help="Overrides BINANCE_API_SECRET env var")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    return parser


def _prompt(label: str, validator, *validator_args):
    """
    Repeatedly prompt for a single field until it passes `validator`.
    Returns the validated value. Ctrl+C / Ctrl+D exits cleanly.
    """
    while True:
        try:
            raw = input(label)
        except (EOFError, KeyboardInterrupt):
            safe_print("\nCancelled.")
            sys.exit(130)
        try:
            return validator(raw, *validator_args) if validator_args else validator(raw)
        except ValidationError as exc:
            safe_print(f"  ⚠ {exc}  — try again.")


def run_interactive() -> OrderRequest:
    """Guided prompt flow: asks one field at a time, validating as it goes."""
    safe_print("=== Interactive Order Builder (Binance Futures Testnet) ===")
    symbol = _prompt("Symbol (e.g. BTCUSDT): ", validate_symbol)
    side = _prompt("Side (BUY/SELL): ", validate_side)
    order_type = _prompt("Order type (MARKET/LIMIT/STOP_LIMIT): ", validate_order_type)
    quantity = _prompt("Quantity: ", validate_quantity)

    price = None
    if order_type in ("LIMIT", "STOP_LIMIT"):
        price = _prompt("Price: ", validate_price, order_type)

    stop_price = None
    if order_type == "STOP_LIMIT":
        stop_price = _prompt("Stop price: ", validate_stop_price, order_type)

    time_in_force = "GTC"
    if order_type in ("LIMIT", "STOP_LIMIT"):
        while True:
            tif = input("Time in force [GTC/IOC/FOK] (default GTC): ").strip().upper() or "GTC"
            if tif in ("GTC", "IOC", "FOK"):
                time_in_force = tif
                break
            safe_print("  ⚠ Must be one of GTC, IOC, FOK — try again.")

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=time_in_force,
    )


def build_order_from_args(args: argparse.Namespace) -> OrderRequest:
    """
    Validates a fully non-interactive argparse namespace and builds an
    OrderRequest. Raises ValidationError (missing OR invalid fields are
    reported the same way) so `main()` has one error-handling path.
    """
    missing = [
        name
        for name, val in (
            ("--symbol", args.symbol),
            ("--side", args.side),
            ("--type", args.order_type),
            ("--quantity", args.quantity),
        )
        if val is None
    ]
    if missing:
        raise ValidationError(
            f"Missing required argument(s): {', '.join(missing)}. "
            "Run with --interactive for guided prompts, or --help for usage."
        )

    symbol = validate_symbol(args.symbol)
    side = validate_side(args.side)
    order_type = validate_order_type(args.order_type)
    quantity = validate_quantity(args.quantity)
    price = validate_price(args.price, order_type)
    stop_price = validate_stop_price(args.stop_price, order_type)

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=quantity,
        price=price,
        stop_price=stop_price,
        time_in_force=args.time_in_force,
    )


def main(argv=None) -> int:
    load_dotenv()  # pulls BINANCE_API_KEY / BINANCE_API_SECRET from a .env file if present

    parser = build_parser()
    args = parser.parse_args(argv)

    # No args at all, or explicit --interactive/-i, both drop into prompt mode.
    interactive = args.interactive or (argv is None and len(sys.argv) == 1)

    try:
        if interactive:
            request = run_interactive()
        else:
            request = build_order_from_args(args)
    except ValidationError as exc:
        logger.error("Input validation failed: %s", exc)
        safe_print(f"❌ Invalid input: {exc}")
        return 1

    api_key = args.api_key or os.getenv("BINANCE_API_KEY")
    api_secret = args.api_secret or os.getenv("BINANCE_API_SECRET")

    if not api_key or not api_secret:
        safe_print(
            "❌ Missing API credentials. Set BINANCE_API_KEY / BINANCE_API_SECRET "
            "(env vars or .env file) or pass --api-key / --api-secret."
        )
        return 1

    try:
        client = BinanceFuturesTestnetClient(api_key, api_secret, base_url=args.base_url)
        manager = OrderManager(client)
        manager.place(request)
        return 0
    except BinanceAPIError:
        return 2
    except NetworkError:
        return 3
    except Exception as exc:  # last-resort safety net; never crash silently
        logger.exception("Unexpected error while placing order")
        safe_print(f"❌ Unexpected error: {exc}")
        return 4


if __name__ == "__main__":
    sys.exit(main())
