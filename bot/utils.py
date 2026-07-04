"""
Rich-powered display utilities for the trading bot CLI.

Uses the `rich` library for styled panels, tables, spinners, and
cross-platform color support (works on Windows cmd, PowerShell, and Unix).
"""

import os
import sys
from typing import Any, Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

# Force UTF-8 output on Windows to avoid cp1252 encoding errors
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(force_terminal=True)

# ------------------------------------------------------------------ #
# Color constants (kept for backward compatibility with existing code)
# ------------------------------------------------------------------ #
GREEN = "[bold green]"
RED = "[bold red]"
YELLOW = "[bold yellow]"
CYAN = "[bold cyan]"
BOLD = "[bold]"
DIM = "[dim]"
RESET = "[/]"


def safe_print(*args, **kwargs) -> None:
    """
    Prints to console using rich markup. Falls back gracefully if
    the terminal doesn't support rich rendering.
    """
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    text = sep.join(str(arg) for arg in args)
    try:
        console.print(text, end=end, highlight=False)
    except Exception:
        import re
        clean = re.sub(r"\[/?[^\]]*\]", "", text)
        print(clean, end=end)


def print_banner() -> None:
    """Print a styled welcome banner for interactive mode."""
    banner_text = Text()
    banner_text.append(" Binance Futures Testnet ", style="bold white on blue")
    banner_text.append("  Trading Bot CLI ", style="bold cyan")

    panel = Panel(
        Align.center(banner_text),
        border_style="cyan",
        box=box.DOUBLE,
        padding=(1, 2),
        subtitle="[dim]USDT-M Futures | Testnet Mode[/dim]",
        subtitle_align="center",
    )
    console.print()
    console.print(panel)
    console.print()


def print_order_summary(symbol: str, side: str, order_type: str,
                        quantity: float, price: Optional[float] = None,
                        stop_price: Optional[float] = None) -> None:
    """Print a rich-formatted order summary table inside a panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="dim", width=14)
    table.add_column("Value", style="bold")

    table.add_row("Symbol", f"[bold white]{symbol}[/]")

    side_style = "bold green" if side == "BUY" else "bold red"
    side_arrow = ">>" if side == "BUY" else "<<"
    table.add_row("Side", f"[{side_style}]{side_arrow} {side}[/]")

    table.add_row("Type", f"[bold]{order_type}[/]")
    table.add_row("Quantity", f"[bold]{quantity}[/]")

    if price is not None:
        table.add_row("Price", f"[bold yellow]{price:,.2f}[/]")
    if stop_price is not None:
        table.add_row("Stop Price", f"[bold yellow]{stop_price:,.2f}[/]")

    panel = Panel(
        table,
        title="[bold cyan]Order Request[/]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)


def print_order_response(response: Dict[str, Any]) -> None:
    """Print a rich-formatted order response table inside a panel."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="dim", width=16)
    table.add_column("Value", style="bold")

    table.add_row("Order ID", f"[bold white]{response.get('orderId')}[/]")

    status = response.get("status", "UNKNOWN")
    status_style = "bold green" if status in ("NEW", "FILLED", "PARTIALLY_FILLED") else "bold yellow"
    table.add_row("Status", f"[{status_style}]{status}[/]")

    table.add_row("Executed Qty", f"{response.get('executedQty', 'N/A')}")

    avg_price = response.get("avgPrice")
    if avg_price is not None and avg_price != "0.00":
        table.add_row("Avg Price", f"[bold yellow]{avg_price}[/]")

    orig_qty = response.get("origQty")
    if orig_qty:
        table.add_row("Original Qty", f"{orig_qty}")

    table.add_row("Client Order ID", f"[dim]{response.get('clientOrderId')}[/]")

    order_type = response.get("type", "")
    if order_type:
        table.add_row("Type", f"{order_type}")

    panel = Panel(
        table,
        title="[bold green]ORDER PLACED SUCCESSFULLY[/]",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 1),
    )
    console.print(panel)
    console.print()


def print_error(message: str, detail: str = "") -> None:
    """Print a styled error message."""
    error_text = Text()
    error_text.append("FAILED: ", style="bold red")
    error_text.append(message, style="bold red")
    if detail:
        error_text.append(f"\n  {detail}", style="red")

    panel = Panel(
        error_text,
        border_style="red",
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print(panel)


def confirm_order() -> bool:
    """Ask the user to confirm before placing the order."""
    try:
        console.print()
        response = console.input(
            "[bold yellow]>> Place this order? [Y/n]: [/]"
        ).strip().lower()
        if response in ("", "y", "yes"):
            return True
        console.print("[dim]Order cancelled by user.[/dim]")
        return False
    except (EOFError, KeyboardInterrupt):
        console.print("\n[dim]Order cancelled.[/dim]")
        return False


def spinner_context(message: str = "Placing order on Binance Futures Testnet..."):
    """
    Returns a context manager that shows a spinner animation while
    the API call is in flight.
    """
    return console.status(f"[bold cyan]{message}[/]", spinner="dots")
