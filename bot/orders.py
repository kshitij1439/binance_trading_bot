"""
High-level order placement logic. Sits between the CLI and the raw REST
client: builds the correct Binance param set per order type, prints a
human-readable summary, and normalizes the response for display/logging.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.client import BinanceAPIError, BinanceFuturesTestnetClient, NetworkError
from bot.logging_config import get_logger

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
        print("\n=== Order Request Summary ===")
        print(f"  Symbol      : {req.symbol}")
        print(f"  Side        : {req.side}")
        print(f"  Type        : {req.order_type}")
        print(f"  Quantity    : {req.quantity}")
        if req.price is not None:
            print(f"  Price       : {req.price}")
        if req.stop_price is not None:
            print(f"  Stop Price  : {req.stop_price}")
        print("==============================\n")

    def place(self, req: OrderRequest) -> Dict[str, Any]:
        self.print_summary(req)
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
            print(f"❌ FAILED: Binance rejected the order — {exc.message} (code={exc.code})")
            raise
        except NetworkError as exc:
            logger.error("Order failed due to network error: %s", exc)
            print(f"❌ FAILED: Network error while placing order — {exc}")
            raise

        self._print_response(response)
        logger.info("Order placed successfully: %s", response)
        return response

    def _print_response(self, response: Dict[str, Any]) -> None:
        print("=== Order Response ===")
        print(f"  Order ID     : {response.get('orderId')}")
        print(f"  Status       : {response.get('status')}")
        print(f"  Executed Qty : {response.get('executedQty')}")
        avg_price = response.get("avgPrice")
        if avg_price is not None:
            print(f"  Avg Price    : {avg_price}")
        print(f"  Client OrderID: {response.get('clientOrderId')}")
        print("=======================")
        print("✅ SUCCESS: Order placed on Binance Futures Testnet.\n")
