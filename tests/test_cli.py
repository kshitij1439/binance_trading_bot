"""
CLI-level tests. The Binance client is mocked out entirely — these tests
verify argument parsing, validation wiring, and exit codes, not real
network behavior (that's exercised manually against the live testnet).
"""

import unittest
from unittest.mock import patch, MagicMock

import cli


class TestNonInteractiveArgs(unittest.TestCase):
    def _run(self, args, mock_response=None, side_effect=None):
        with patch("cli.BinanceFuturesTestnetClient") as MockClient:
            instance = MockClient.return_value
            if side_effect is not None:
                instance.place_order.side_effect = side_effect
            else:
                instance.place_order.return_value = mock_response or {
                    "orderId": 1,
                    "status": "FILLED",
                    "executedQty": "0.01",
                    "avgPrice": "65000.0",
                    "clientOrderId": "x-test",
                }
            return cli.main(args + ["--api-key", "k", "--api-secret", "s"])

    def test_valid_market_order_returns_zero(self):
        exit_code = self._run(
            ["--symbol", "BTCUSDT", "--side", "BUY", "--type", "MARKET", "--quantity", "0.01"]
        )
        self.assertEqual(exit_code, 0)

    def test_valid_limit_order_returns_zero(self):
        exit_code = self._run(
            [
                "--symbol", "BTCUSDT", "--side", "SELL", "--type", "LIMIT",
                "--quantity", "0.01", "--price", "65000",
            ]
        )
        self.assertEqual(exit_code, 0)

    def test_missing_price_for_limit_returns_one(self):
        exit_code = self._run(
            ["--symbol", "BTCUSDT", "--side", "SELL", "--type", "LIMIT", "--quantity", "0.01"]
        )
        self.assertEqual(exit_code, 1)

    def test_missing_required_field_returns_one(self):
        exit_code = self._run(["--symbol", "BTCUSDT", "--side", "BUY", "--quantity", "0.01"])
        self.assertEqual(exit_code, 1)

    def test_invalid_symbol_returns_one(self):
        exit_code = self._run(
            ["--symbol", "BTC", "--side", "BUY", "--type", "MARKET", "--quantity", "0.01"]
        )
        self.assertEqual(exit_code, 1)

    def test_missing_credentials_returns_one(self):
        with patch("cli.BinanceFuturesTestnetClient"):
            with patch.dict("os.environ", {}, clear=True):
                exit_code = cli.main(
                    ["--symbol", "BTCUSDT", "--side", "BUY", "--type", "MARKET", "--quantity", "0.01"]
                )
        self.assertEqual(exit_code, 1)

    def test_binance_api_error_returns_two(self):
        from bot.client import BinanceAPIError

        exit_code = self._run(
            ["--symbol", "BTCUSDT", "--side", "BUY", "--type", "MARKET", "--quantity", "0.01"],
            side_effect=BinanceAPIError(400, -2010, "Account has insufficient balance"),
        )
        self.assertEqual(exit_code, 2)

    def test_network_error_returns_three(self):
        from bot.client import NetworkError

        exit_code = self._run(
            ["--symbol", "BTCUSDT", "--side", "BUY", "--type", "MARKET", "--quantity", "0.01"],
            side_effect=NetworkError("connection timed out"),
        )
        self.assertEqual(exit_code, 3)


class TestBuildOrderFromArgs(unittest.TestCase):
    def test_stop_limit_requires_stop_price(self):
        parser = cli.build_parser()
        args = parser.parse_args(
            [
                "--symbol", "BTCUSDT", "--side", "SELL", "--type", "STOP_LIMIT",
                "--quantity", "0.01", "--price", "60000",
            ]
        )
        with self.assertRaises(cli.ValidationError):
            cli.build_order_from_args(args)

    def test_valid_stop_limit_builds_request(self):
        parser = cli.build_parser()
        args = parser.parse_args(
            [
                "--symbol", "BTCUSDT", "--side", "SELL", "--type", "STOP_LIMIT",
                "--quantity", "0.01", "--price", "60000", "--stop-price", "60500",
            ]
        )
        request = cli.build_order_from_args(args)
        self.assertEqual(request.symbol, "BTCUSDT")
        self.assertEqual(request.stop_price, 60500.0)


if __name__ == "__main__":
    unittest.main()
