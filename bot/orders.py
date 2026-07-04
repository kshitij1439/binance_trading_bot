"""
High-level order placement logic. Sits between the CLI and the raw REST
client: builds the correct Binance param set per order type, prints a
human-readable summary, and normalizes the response for display/logging.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.client import BinanceAPIError, BinanceFuturesTestnetClient, NetworkError
from bot.logging_config import get_logger
from bot.utils import safe_print, confirm_order, BOLD, CYAN, GREEN, RED, YELLOW, DIM, RESET

logger = get_logger(__name__)


@dataclass
class OrderRequest:
    symbol: str
    side: str  # BUY / SELL
    order_type: str  # MARKET / LIMIT / STOP_LIMIT
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "GTC"

    def to_binance_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
        }

        if self.order_type == "MARKET":
            params["type"] = "MARKET"
        elif self.order_type == "LIMIT":
            params.update(
                {
                    "type": "LIMIT",
                    "price": self.price,
                    "timeInForce": self.time_in_force,
                }
            )
        elif self.order_type == "STOP_LIMIT":
            # Binance futures uses type=STOP for a stop-limit order
            params.update(
                {
                    "type": "STOP",
                    "price": self.price,
                    "stopPrice": self.stop_price,
                    "timeInForce": self.time_in_force,
                }
            )
        else:
            raise ValueError(f"Unsupported order type: {self.order_type}")

        return params


class OrderManager:
    def __init__(self, client: BinanceFuturesTestnetClient):
        self.client = client

    def print_summary(self, req: OrderRequest) -> None:
        safe_print(f"\n{CYAN}{BOLD}=== Order Request Summary ==={RESET}")
        safe_print(f"  Symbol      : {BOLD}{req.symbol}{RESET}")
        side_color = GREEN if req.side == "BUY" else RED
        safe_print(f"  Side        : {side_color}{BOLD}{req.side}{RESET}")
        safe_print(f"  Type        : {req.order_type}")
        safe_print(f"  Quantity    : {req.quantity}")
        if req.price is not None:
            safe_print(f"  Price       : {req.price}")
        if req.stop_price is not None:
            safe_print(f"  Stop Price  : {req.stop_price}")
        safe_print(f"{CYAN}=============================={RESET}")

    def place(self, req: OrderRequest, skip_confirm: bool = False) -> Dict[str, Any]:
        self.print_summary(req)

        if not skip_confirm and not confirm_order():
            logger.info("Order cancelled by user before placement.")
            return {}
        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s stop_price=%s",
            req.order_type,
            req.side,
            req.symbol,
            req.quantity,
            req.price,
            req.stop_price,
        )

        try:
            response = self.client.place_order(**req.to_binance_params())
        except BinanceAPIError as exc:
            logger.error("Order rejected by Binance: %s", exc)
            safe_print(f"{RED}{BOLD}❌ FAILED:{RESET}{RED} Binance rejected the order — {exc.message} (code={exc.code}){RESET}")
            raise
        except NetworkError as exc:
            logger.error("Order failed due to network error: %s", exc)
            safe_print(f"{RED}{BOLD}❌ FAILED:{RESET}{RED} Network error while placing order — {exc}{RESET}")
            raise

        self._print_response(response)
        logger.info("Order placed successfully: %s", response)
        return response

    def _print_response(self, response: Dict[str, Any]) -> None:
        safe_print(f"\n{CYAN}{BOLD}=== Order Response ==={RESET}")
        safe_print(f"  Order ID     : {BOLD}{response.get('orderId')}{RESET}")
        safe_print(f"  Status       : {GREEN}{response.get('status')}{RESET}")
        safe_print(f"  Executed Qty : {response.get('executedQty')}")
        avg_price = response.get("avgPrice")
        if avg_price is not None:
            safe_print(f"  Avg Price    : {avg_price}")
        safe_print(f"  Client OrderID: {DIM}{response.get('clientOrderId')}{RESET}")
        safe_print(f"{CYAN}======================={RESET}")
        safe_print(f"{GREEN}{BOLD}✅ SUCCESS: Order placed on Binance Futures Testnet.{RESET}\n")
