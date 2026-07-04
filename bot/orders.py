"""
High-level order placement logic. Sits between the CLI and the raw REST
client: builds the correct Binance param set per order type, prints a
human-readable summary, and normalizes the response for display/logging.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.client import BinanceAPIError, BinanceFuturesTestnetClient, NetworkError
from bot.logging_config import get_logger
from bot.utils import (
    print_order_summary,
    print_order_response,
    print_error,
    confirm_order,
    spinner_context,
    console,
)

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

    def place(self, req: OrderRequest, skip_confirm: bool = False) -> Dict[str, Any]:
        # Display rich order summary panel
        print_order_summary(
            symbol=req.symbol,
            side=req.side,
            order_type=req.order_type,
            quantity=req.quantity,
            price=req.price,
            stop_price=req.stop_price,
        )

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
            # Show spinner animation while API call is in flight
            with spinner_context():
                response = self.client.place_order(**req.to_binance_params())
        except BinanceAPIError as exc:
            logger.error("Order rejected by Binance: %s", exc)
            print_error(
                "Binance rejected the order",
                f"{exc.message} (code={exc.code})"
            )
            raise
        except NetworkError as exc:
            logger.error("Order failed due to network error: %s", exc)
            print_error(
                "Network error while placing order",
                str(exc)
            )
            raise

        # Display rich order response panel
        print_order_response(response)
        logger.info("Order placed successfully: %s", response)
        return response
