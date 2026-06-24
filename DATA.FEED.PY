"""
Fetch price data from Binance using the ccxt library
(no API key needed since we only read public candle data)
"""

import ccxt
import pandas as pd

exchange = ccxt.binance()


def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
    """
    Fetch candles from Binance.
    symbol must be in ccxt format like 'BTC/USDT' (not BTCUSDT) -- handled automatically.
    """
    ccxt_symbol = to_ccxt_symbol(symbol)
    raw = exchange.fetch_ohlcv(ccxt_symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def to_ccxt_symbol(symbol: str) -> str:
    """Convert 'BTCUSDT' to 'BTC/USDT' for use with ccxt."""
    if "/" in symbol:
        return symbol
    if symbol.endswith("USDT"):
        return f"{symbol[:-4]}/USDT"
    if symbol.endswith("BUSD"):
        return f"{symbol[:-4]}/BUSD"
    return symbol


def fetch_last_price(symbol: str) -> float:
    """Latest live price for a symbol."""
    ccxt_symbol = to_ccxt_symbol(symbol)
    ticker = exchange.fetch_ticker(ccxt_symbol)
    return ticker["last"]


# Leveraged token keywords that should be excluded from the altcoin scan list
_LEVERAGED_KEYWORDS = ("UP/", "DOWN/", "BULL/", "BEAR/")


def fetch_all_usdt_spot_symbols(exclude_leveraged: bool = True) -> list:
    """
    Return all USDT-quoted spot trading pairs on Binance.
    Output is in simple format like 'BTCUSDT' (not ccxt format).
    """
    markets = exchange.load_markets()
    symbols = []
    for ccxt_symbol, market in markets.items():
        if not market.get("spot", False):
            continue
        if market.get("quote") != "USDT":
            continue
        if not market.get("active", True):
            continue
        if exclude_leveraged and any(k in ccxt_symbol for k in _LEVERAGED_KEYWORDS):
            continue
        symbols.append(market["base"] + market["quote"])  # e.g. BTCUSDT
    return sorted(set(symbols))
