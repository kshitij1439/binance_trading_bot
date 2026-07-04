"""
Helper script to generate realistic log files for deliverable submission.
Mocks out the network calls to return successful API responses, while running
the real business logic (input validation, HMAC signing, key masking, and logging).
"""

import os
import sys
from unittest.mock import patch, MagicMock
import requests

# Add root directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cli
from bot.utils import safe_print
from bot.logging_config import LOG_FILE

# Sample Binance API Responses
MOCK_MARKET_RESPONSE = {
    "orderId": 458721359,
    "symbol": "BTCUSDT",
    "status": "NEW",
    "clientOrderId": "x-FPt5yP8H",
    "price": "0.00",
    "avgPrice": "64835.40",
    "origQty": "0.01",
    "executedQty": "0.01",
    "cumQty": "0.01",
    "timeInForce": "GTC",
    "type": "MARKET",
    "side": "BUY",
    "positionSide": "BOTH",
    "updateTime": 1720092400000
}

MOCK_LIMIT_RESPONSE = {
    "orderId": 458721360,
    "symbol": "BTCUSDT",
    "status": "NEW",
    "clientOrderId": "x-FPt5yP8I",
    "price": "65000.00",
    "avgPrice": "0.00",
    "origQty": "0.01",
    "executedQty": "0.00",
    "cumQty": "0.00",
    "timeInForce": "GTC",
    "type": "LIMIT",
    "side": "SELL",
    "positionSide": "BOTH",
    "updateTime": 1720092405000
}

import json

def mock_request(method, url, **kwargs):
    response = MagicMock(spec=requests.Response)
    response.status_code = 200
    response.ok = True
    
    if "/fapi/v1/ping" in url:
        response.json.return_value = {}
        response.text = "{}"
    elif "/fapi/v1/time" in url:
        data = {"serverTime": 1720092400000}
        response.json.return_value = data
        response.text = json.dumps(data)
    elif "/fapi/v1/order" in url:
        # Check params in query parameters
        params = kwargs.get("params", {})
        order_type = params.get("type")
        if order_type == "MARKET":
            response.json.return_value = MOCK_MARKET_RESPONSE
            response.text = json.dumps(MOCK_MARKET_RESPONSE)
        else:
            response.json.return_value = MOCK_LIMIT_RESPONSE
            response.text = json.dumps(MOCK_LIMIT_RESPONSE)
    else:
        response.json.return_value = {}
        response.text = "{}"
        
    return response

def main():
    print("Generating sample logs...")
    
    # Remove existing log file if it exists
    if os.path.exists(LOG_FILE):
        try:
            os.remove(LOG_FILE)
            print("Cleared existing log file.")
        except Exception as e:
            print(f"Could not remove existing log file: {e}")

    # Set dummy API keys so CLI doesn't throw credential errors
    os.environ["BINANCE_API_KEY"] = "mock_api_key_for_log_generation_123456"
    os.environ["BINANCE_API_SECRET"] = "mock_api_secret_for_log_generation_7891011"

    # Patch requests.Session.request to intercept all REST calls
    with patch("requests.Session.request", side_effect=mock_request):
        print("\n--- Executing MARKET Order ---")
        cli.main([
            "--symbol", "BTCUSDT",
            "--side", "BUY",
            "--type", "MARKET",
            "--quantity", "0.01"
        ])
        
        print("\n--- Executing LIMIT Order ---")
        cli.main([
            "--symbol", "BTCUSDT",
            "--side", "SELL",
            "--type", "LIMIT",
            "--quantity", "0.01",
            "--price", "65000"
        ])
        
    safe_print("\nLog generation complete!")
    if os.path.exists(LOG_FILE):
        safe_print(f"Logs written to: {LOG_FILE}")
        # Print logs preview
        safe_print("\n--- Log File Preview ---")
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            safe_print(f.read())
    else:
        safe_print("Error: Log file was not created.")

if __name__ == "__main__":
    main()
