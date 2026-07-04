# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application that places **Market**, **Limit**,
and **Stop-Limit** orders on Binance Futures Testnet, with input validation,
structured logging, and clean error handling.

## Project Structure

```
trading_bot/
  bot/
    __init__.py
    client.py          # Signed REST client (requests + HMAC-SHA256)
    orders.py           # Order building, placement, response formatting
    validators.py       # CLI input validation
    logging_config.py   # File + console logging setup
  cli.py                # CLI entry point (argparse)
  logs/
    trading_bot.log     # Generated at runtime — every request/response/error
  requirements.txt
  .env.example
  README.md
```

**Why direct REST instead of `python-binance`?** The task requires logging
every API request and response. A raw `requests`-based client with manual
HMAC signing keeps that fully visible and loggable, rather than hidden
inside a third-party SDK.

## Setup

### 1. Create a Binance Futures Testnet account
1. Go to https://testnet.binancefuture.com
2. Log in with a GitHub account (this is how the testnet handles auth).
3. Go to **API Key** management on the testnet dashboard and generate an
   API Key + Secret. (Note: testnet keys are separate from real Binance
   account keys and only work against the testnet base URL.)

### 2. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure credentials

```bash
cp .env.example .env
# then edit .env and paste your testnet API key/secret
```

`.env` is loaded automatically via `python-dotenv`. Alternatively, export
env vars directly, or pass `--api-key` / `--api-secret` on the command line.

## Usage

### Market order

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

### Limit order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

### Stop-Limit order (bonus order type)

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_LIMIT \
    --quantity 0.01 --price 60000 --stop-price 60500
```

### Interactive mode (bonus CLI UX)

Run with no arguments, or with `--interactive` / `-i`, for guided
step-by-step prompts with live validation on each field:

```bash
python cli.py --interactive
```

```
=== Interactive Order Builder (Binance Futures Testnet) ===
Symbol (e.g. BTCUSDT): btc
  ⚠ Invalid symbol 'BTC'. Expected format like 'BTCUSDT' (5-20 alphanumeric chars).  — try again.
Symbol (e.g. BTCUSDT): BTCUSDT
Side (BUY/SELL): BUY
Order type (MARKET/LIMIT/STOP_LIMIT): LIMIT
Quantity: 0.01
Price: 65000
Time in force [GTC/IOC/FOK] (default GTC):
```

Each field re-prompts on invalid input instead of exiting, so a typo
doesn't cost you the whole run.

### All CLI options

```
--symbol         Trading pair, e.g. BTCUSDT              (required)
--side           BUY | SELL                              (required)
--type           MARKET | LIMIT | STOP_LIMIT              (required)
--quantity       Order quantity                           (required)
--price          Required for LIMIT / STOP_LIMIT
--stop-price     Required for STOP_LIMIT only
--time-in-force  GTC | IOC | FOK   (default: GTC)
--api-key        Overrides BINANCE_API_KEY env var
--api-secret     Overrides BINANCE_API_SECRET env var
--base-url       Override API base URL (default: https://testnet.binancefuture.com)
```

### Sample output

```
=== Order Request Summary ===
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.01
==============================

=== Order Response ===
  Order ID     : 3457812345
  Status       : FILLED
  Executed Qty : 0.01
  Avg Price    : 64832.10
  Client OrderID: x-abc123
=======================
✅ SUCCESS: Order placed on Binance Futures Testnet.
```

On failure (bad input, rejected order, or network issue) the CLI prints a
`❌` message and exits with a non-zero status code (`1` = validation error,
`2` = Binance API error, `3` = network error, `4` = unexpected error).

## Running in Docker (optional)

Not required to satisfy the task, but included for a fully reproducible
runtime:

```bash
docker build -t binance-trading-bot .
docker run --env-file .env binance-trading-bot \
    --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

Note: the container writes logs to `/app/logs` inside the container, which
disappears when the container exits unless you mount a volume:

```bash
docker run --env-file .env -v "$(pwd)/logs:/app/logs" binance-trading-bot \
    --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

## Running tests

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The CLI tests (`tests/test_cli.py`) mock the Binance client entirely, so
they run offline and don't touch the real testnet. The validator tests
(`tests/test_validators.py`) are pure unit tests.

## Logging

Every request, response, and error is written to `logs/trading_bot.log`
(rotated at 2MB, 5 backups kept), including:
- Full outgoing request params (API secret is never logged; the API key is
  masked, e.g. `test...3456`)
- Full raw response body and HTTP status
- Retry attempts on network failures (up to 3, with exponential backoff)
- Any validation or API errors

The console only shows INFO-level messages so normal runs stay readable;
full detail always goes to the log file.

## Error Handling

- **Invalid input** (bad symbol format, missing price for LIMIT, etc.) is
  caught before any network call is made — see `bot/validators.py`.
- **API errors** (e.g. insufficient margin, invalid quantity precision,
  bad symbol) raise `BinanceAPIError` with the exact Binance error code/message.
- **Network errors** (timeouts, DNS failures, connection drops) are retried
  up to 3 times with backoff, then raised as `NetworkError`.
- All exceptions are logged with full context before the CLI exits cleanly
  — the app never crashes with a raw traceback for expected failure modes.

## Assumptions

- Symbol precision/lot-size rules (e.g. minimum quantity step for BTCUSDT)
  are enforced by Binance itself; the client passes through whatever the
  user provides and surfaces Binance's rejection message if it's invalid.
- `timeInForce` defaults to `GTC` for LIMIT/STOP-LIMIT orders and is
  configurable via `--time-in-force`.
- Only USDT-M Futures Testnet is targeted (`/fapi/v1/...` endpoints), not
  Spot or Coin-M testnet.
- STOP_LIMIT is implemented as Binance's `STOP` order type (limit order that
  triggers once `stopPrice` is touched), which is the futures equivalent of
  a stop-limit order.
- No API credentials are committed to the repo; `.env` is gitignored, and
  `.env.example` documents the required variables.

## Getting the required log files (Deliverable #2)

Run one MARKET and one LIMIT order against your own testnet credentials:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000
```

Then include the resulting `logs/trading_bot.log` (or copies renamed
`market_order.log` / `limit_order.log`) in the submission.
