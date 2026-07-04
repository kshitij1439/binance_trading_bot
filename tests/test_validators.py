"""
Unit tests for bot/validators.py — run with:
    python -m unittest discover -s tests
"""

import unittest

from bot.validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)


class TestSymbolValidation(unittest.TestCase):
    def test_valid_symbol(self):
        self.assertEqual(validate_symbol("btcusdt"), "BTCUSDT")

    def test_invalid_symbol_too_short(self):
        with self.assertRaises(ValidationError):
            validate_symbol("BTC")

    def test_invalid_symbol_special_chars(self):
        with self.assertRaises(ValidationError):
            validate_symbol("BTC-USDT")


class TestSideValidation(unittest.TestCase):
    def test_valid_sides(self):
        self.assertEqual(validate_side("buy"), "BUY")
        self.assertEqual(validate_side("SELL"), "SELL")

    def test_invalid_side(self):
        with self.assertRaises(ValidationError):
            validate_side("HOLD")


class TestOrderTypeValidation(unittest.TestCase):
    def test_valid_types(self):
        self.assertEqual(validate_order_type("market"), "MARKET")
        self.assertEqual(validate_order_type("LIMIT"), "LIMIT")
        self.assertEqual(validate_order_type("stop_limit"), "STOP_LIMIT")

    def test_invalid_type(self):
        with self.assertRaises(ValidationError):
            validate_order_type("OCO")


class TestQuantityValidation(unittest.TestCase):
    def test_valid_quantity(self):
        self.assertEqual(validate_quantity("0.01"), 0.01)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            validate_quantity(0)

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            validate_quantity(-5)

    def test_non_numeric_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            validate_quantity("abc")


class TestPriceValidation(unittest.TestCase):
    def test_market_order_requires_no_price(self):
        self.assertIsNone(validate_price(None, "MARKET"))

    def test_market_order_rejects_price(self):
        with self.assertRaises(ValidationError):
            validate_price(100, "MARKET")

    def test_limit_order_requires_price(self):
        with self.assertRaises(ValidationError):
            validate_price(None, "LIMIT")

    def test_limit_order_valid_price(self):
        self.assertEqual(validate_price("65000", "LIMIT"), 65000.0)


class TestStopPriceValidation(unittest.TestCase):
    def test_not_required_for_market(self):
        self.assertIsNone(validate_stop_price(None, "MARKET"))

    def test_required_for_stop_limit(self):
        with self.assertRaises(ValidationError):
            validate_stop_price(None, "STOP_LIMIT")

    def test_valid_stop_price(self):
        self.assertEqual(validate_stop_price("60500", "STOP_LIMIT"), 60500.0)


if __name__ == "__main__":
    unittest.main()
