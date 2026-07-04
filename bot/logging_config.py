"""
Centralized logging configuration.

- All API requests, responses, and errors are logged to `logs/trading_bot.log`.
- A concise INFO-level summary is also echoed to the console.
- Log file uses rotation so it never grows unbounded across many runs.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str = "trading_bot") -> logging.Logger:
    """
    Returns a configured logger. Safe to call multiple times (handlers are
    only attached once per logger name).
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured (e.g. imported in multiple modules)
        return logger

    logger.setLevel(logging.DEBUG)

    file_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_format = logging.Formatter("%(levelname)-8s | %(message)s")

    # Rotating file handler: full detail (DEBUG+), keeps last 5 files @ 2MB
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_format)

    # Console handler: only INFO+ to keep terminal output clean/non-noisy
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_format)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False

    return logger
