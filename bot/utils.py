"""
Utility functions for the trading bot.
"""

import os
import sys


def _supports_color() -> bool:
    """Check if the terminal supports ANSI color codes."""
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    if sys.platform == "win32":
        # Windows 10+ supports ANSI via virtual terminal processing
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable virtual terminal processing
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return True


# ANSI color codes
_COLOR = _supports_color()
GREEN = "\033[92m" if _COLOR else ""
RED = "\033[91m" if _COLOR else ""
YELLOW = "\033[93m" if _COLOR else ""
CYAN = "\033[96m" if _COLOR else ""
BOLD = "\033[1m" if _COLOR else ""
DIM = "\033[2m" if _COLOR else ""
RESET = "\033[0m" if _COLOR else ""


def safe_print(*args, **kwargs) -> None:
    """
    Prints to standard output, falling back to ASCII/safe characters if the
    system console encoding (e.g., cp1252 or cp850 on Windows) does not support
    Unicode emojis.
    """
    sep = kwargs.get("sep", " ")
    text = sep.join(str(arg) for arg in args)

    # Try printing normally first
    try:
        kwargs_no_sep = {k: v for k, v in kwargs.items() if k != "sep"}
        print(text, **kwargs_no_sep)
    except UnicodeEncodeError:
        # Fallback to ascii/safe characters
        safe_text = (
            text.replace("\u274c", "[FAILED]")
            .replace("\u2705", "[SUCCESS]")
            .replace("\u26a0", "[WARNING]")
            .replace("\u2554", "+")
            .replace("\u2557", "+")
            .replace("\u255a", "+")
            .replace("\u255d", "+")
            .replace("\u2550", "=")
            .replace("\u2551", "|")
        )
        encoding = sys.stdout.encoding or "utf-8"
        encoded = safe_text.encode(encoding, errors="replace")
        decoded = encoded.decode(encoding)
        kwargs_no_sep = {k: v for k, v in kwargs.items() if k != "sep"}
        print(decoded, **kwargs_no_sep)


def print_banner() -> None:
    """Print a styled welcome banner for interactive mode."""
    safe_print(f"\n{CYAN}{BOLD}")
    safe_print("\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557")
    safe_print("\u2551  Binance Futures Testnet \u2014 Trading Bot CLI   \u2551")
    safe_print("\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d")
    safe_print(f"{RESET}")


def confirm_order() -> bool:
    """Ask the user to confirm before placing the order. Returns True if confirmed."""
    try:
        response = input(f"\n{YELLOW}{BOLD}\u26a0 Place this order? [Y/n]: {RESET}").strip().lower()
        if response in ("", "y", "yes"):
            return True
        safe_print(f"{DIM}Order cancelled by user.{RESET}")
        return False
    except (EOFError, KeyboardInterrupt):
        safe_print(f"\n{DIM}Order cancelled.{RESET}")
        return False
