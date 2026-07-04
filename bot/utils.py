"""
Utility functions for the trading bot.
"""

import sys

def safe_print(*args, **kwargs) -> None:
    """
    Prints to standard output, falling back to ASCII/safe characters if the
    system console encoding (e.g., cp1252 or cp850 on Windows) does not support
    Unicode emojis.
    """
    sep = kwargs.get("sep", " ")
    text = sep.join(str(arg) for arg in args)
    
    # Try printing normally first
    try:
        # We need to print without our custom sep since we already joined
        kwargs_no_sep = {k: v for k, v in kwargs.items() if k != "sep"}
        print(text, **kwargs_no_sep)
    except UnicodeEncodeError:
        # Fallback to ascii/safe characters
        safe_text = (
            text.replace("❌", "[FAILED]")
            .replace("✅", "[SUCCESS]")
            .replace("⚠", "[WARNING]")
        )
        encoding = sys.stdout.encoding or "utf-8"
        # Replace any other unencodable characters with '?' or their closest representation
        encoded = safe_text.encode(encoding, errors="replace")
        decoded = encoded.decode(encoding)
        kwargs_no_sep = {k: v for k, v in kwargs.items() if k != "sep"}
        print(decoded, **kwargs_no_sep)
