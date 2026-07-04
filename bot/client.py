"""
Thin, dependency-light REST client for Binance Futures Testnet (USDT-M).

Deliberately implemented with `requests` + manual HMAC signing (instead of
python-binance) so that every request and response can be logged verbatim,
which is a hard requirement of the task.

Docs: https://binance-docs.github.io/apidocs/testnet/en/
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW_MS = 5000
REQUEST_TIMEOUT_S = 10
MAX_RETRIES = 3
RETRY_BACKOFF_S = 1.5


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response with an error payload."""

    def __init__(self, status_code: int, code: Optional[int], message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API error [{status_code}] code={code}: {message}")


class NetworkError(Exception):
    """Raised on connection/timeout failures after retries are exhausted."""


class BinanceFuturesTestnetClient:
    """
    Minimal signed REST client for Binance USDT-M Futures Testnet.

    Only the endpoints needed by this task are implemented:
      - GET  /fapi/v1/ping           (connectivity check)
      - GET  /fapi/v1/time           (server time, used for signing)
      - POST /fapi/v1/order          (place order)
      - GET  /fapi/v1/order          (query order status)
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = DEFAULT_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must both be provided.")
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ---------------------------------------------------------------- #
    # internals
    # ---------------------------------------------------------------- #

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", RECV_WINDOW_MS)
        query = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret, query.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params.copy() if params else {}

        if signed:
            params = self._sign(params)

        # Log the outgoing request. API secret is never included in params,
        # and the key itself is masked for safety.
        safe_headers = {"X-MBX-APIKEY": self._mask(self.api_key)}
        logger.debug(
            "REQUEST %s %s | params=%s | headers=%s", method, url, params, safe_headers
        )

        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.request(
                    method, url, params=params, timeout=REQUEST_TIMEOUT_S
                )
                logger.debug(
                    "RESPONSE %s %s | status=%s | body=%s",
                    method,
                    url,
                    response.status_code,
                    response.text,
                )

                if response.ok:
                    return response.json()

                # Binance error payloads look like: {"code": -2010, "msg": "..."}
                try:
                    payload = response.json()
                    code = payload.get("code")
                    msg = payload.get("msg", response.text)
                except ValueError:
                    code, msg = None, response.text

                logger.error(
                    "API error on %s %s -> status=%s code=%s msg=%s",
                    method,
                    path,
                    response.status_code,
                    code,
                    msg,
                )
                raise BinanceAPIError(response.status_code, code, msg)

            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logger.warning(
                    "Network error on attempt %d/%d for %s %s: %s",
                    attempt,
                    MAX_RETRIES,
                    method,
                    path,
                    exc,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_S * attempt)

        logger.error("Network error: exhausted %d retries for %s %s", MAX_RETRIES, method, path)
        raise NetworkError(f"Failed to reach {url} after {MAX_RETRIES} attempts: {last_exc}")

    @staticmethod
    def _mask(value: str) -> str:
        if not value or len(value) <= 8:
            return "****"
        return f"{value[:4]}...{value[-4:]}"

    # ---------------------------------------------------------------- #
    # public endpoints
    # ---------------------------------------------------------------- #

    def ping(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/ping")

    def server_time(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/time")

    def place_order(self, **params) -> Dict[str, Any]:
        """
        POST /fapi/v1/order

        Expected keys (subset used by this bot):
          symbol, side, type, quantity, price, timeInForce, stopPrice
        """
        # Drop keys with None values; Binance rejects unexpected null params.
        clean_params = {k: v for k, v in params.items() if v is not None}
        return self._request("POST", "/fapi/v1/order", clean_params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        return self._request(
            "GET", "/fapi/v1/order", {"symbol": symbol, "orderId": order_id}, signed=True
        )
