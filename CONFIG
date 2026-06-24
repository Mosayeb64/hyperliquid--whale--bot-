"""
Trading bot configuration.
All adjustable parameters live here so you don't need to touch the core logic.
"""

import os

# ----------------------------------------------------------------------------
# Telegram
# ----------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "PUT_YOUR_CHAT_ID_HERE")

# ----------------------------------------------------------------------------
# Symbols
# ----------------------------------------------------------------------------
# If True, scan all Binance USDT spot pairs (excluding leveraged tokens)
SCAN_ALL_USDT_PAIRS = True

# If SCAN_ALL_USDT_PAIRS is False, only this fixed list is checked
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

# ----------------------------------------------------------------------------
# Timeframes by role in the strategy
# ----------------------------------------------------------------------------
STRUCTURE_TIMEFRAMES = ["1d", "4h"]  # main trend / structure detection
TRIGGER_TIMEFRAME = "1h"             # entry trigger timeframe (RSI, order block return)

# ----------------------------------------------------------------------------
# RSI settings
# ----------------------------------------------------------------------------
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# ----------------------------------------------------------------------------
# Structure break detection settings
# ----------------------------------------------------------------------------
SWING_LOOKBACK = 5

# ----------------------------------------------------------------------------
# Order block settings
# ----------------------------------------------------------------------------
ORDER_BLOCK_IMPULSE_ATR_MULT = 1.5  # minimum impulse move size, as a multiple of ATR
ORDER_BLOCK_ATR_PERIOD = 14

# ----------------------------------------------------------------------------
# Stop loss: how many recent 1H candles to scan for the "last low"
# ----------------------------------------------------------------------------
STOP_LOSS_LOOKBACK_CANDLES = 5
STOP_LOSS_BUFFER_PERCENT = 0.1  # extra percent below the low, to avoid stop hunts

# ----------------------------------------------------------------------------
# Smart money confirmation: trigger candle volume must be N times the previous candle
# ----------------------------------------------------------------------------
SMART_MONEY_VOLUME_MULTIPLIER = 3.0

# ----------------------------------------------------------------------------
# Manual price alerts (optional)
# ----------------------------------------------------------------------------
PRICE_ALERTS = [
    # {"symbol": "BTCUSDT", "price": 70000, "direction": "above"},
]

# ----------------------------------------------------------------------------
# Seconds between each full market scan (per your request: 60 minutes)
# ----------------------------------------------------------------------------
CHECK_INTERVAL_SECONDS = 3600

# Number of candles fetched per timeframe
CANDLES_LIMIT = 200
