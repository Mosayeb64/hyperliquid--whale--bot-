"""
Strategy logic:
- RSI calculation
- RSI divergence detection
- Price structure break detection (simplified CHoCH)
- Order block detection (last candle before a strong impulse move)
- Smart money volume confirmation
"""

import pandas as pd
import numpy as np


def calculate_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    """Standard RSI using Wilder's smoothing (exponential moving average)."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def find_swing_points(series: pd.Series, lookback: int = 5):
    """
    Find swing highs and lows.
    A point is a swing high if it's higher than `lookback` candles before and after it.
    Returns a list of (index, value, type) where type is 'high' or 'low'.
    """
    swings = []
    n = len(series)
    for i in range(lookback, n - lookback):
        window = series.iloc[i - lookback: i + lookback + 1]
        center = series.iloc[i]
        if center == window.max():
            swings.append((i, center, "high"))
        elif center == window.min():
            swings.append((i, center, "low"))
    return swings


def detect_structure_break(df: pd.DataFrame, lookback: int = 5):
    """
    Simplified structure break detection (similar to CHoCH):
    If the latest closed candle closes above the last valid swing high -> bullish structure break.
    If the latest closed candle closes below the last valid swing low -> bearish structure break.

    Returns None or a dict with the signal details.
    """
    highs = find_swing_points(df["high"], lookback)
    lows = find_swing_points(df["low"], lookback)

    swing_highs = [s for s in highs if s[2] == "high"]
    swing_lows = [s for s in lows if s[2] == "low"]

    if not swing_highs or not swing_lows:
        return None

    last_close = df["close"].iloc[-1]
    last_swing_high = swing_highs[-1][1]
    last_swing_low = swing_lows[-1][1]

    if last_close > last_swing_high:
        return {
            "type": "bullish_structure_break",
            "broken_level": last_swing_high,
            "close": last_close,
        }
    elif last_close < last_swing_low:
        return {
            "type": "bearish_structure_break",
            "broken_level": last_swing_low,
            "close": last_close,
        }
    return None


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range, used to measure the strength of a move (impulse)."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def find_order_blocks(df: pd.DataFrame, impulse_atr_mult: float = 1.5, atr_period: int = 14):
    """
    Order block detection: the last candle before a strong impulse move.
    A move is considered an impulse if the close-to-close change between two
    consecutive candles is at least `impulse_atr_mult` times the ATR.

    Returns a list of dicts with the order block candle index, type
    (bullish/bearish), and its high/low range.
    """
    atr = calculate_atr(df, atr_period)
    order_blocks = []

    for i in range(atr_period, len(df) - 1):
        if pd.isna(atr.iloc[i]):
            continue
        move = df["close"].iloc[i + 1] - df["close"].iloc[i]
        if abs(move) >= impulse_atr_mult * atr.iloc[i]:
            ob_type = "bullish" if move > 0 else "bearish"
            order_blocks.append({
                "index": i,
                "type": ob_type,
                "high": df["high"].iloc[i],
                "low": df["low"].iloc[i],
                "timestamp": df["timestamp"].iloc[i] if "timestamp" in df.columns else None,
            })
    return order_blocks


def is_order_block_valid(df: pd.DataFrame, order_block: dict) -> bool:
    """
    An order block is "valid" (unmitigated) if price has not fully traded
    through it since it formed.
    - Bullish: close must not have gone below the order block's low
    - Bearish: close must not have gone above the order block's high
    """
    after = df.iloc[order_block["index"] + 1: -1]  # keep the last candle separate for the return check
    if after.empty:
        return True

    if order_block["type"] == "bullish":
        return not (after["close"] < order_block["low"]).any()
    else:
        return not (after["close"] > order_block["high"]).any()


def get_nearest_valid_order_block(df: pd.DataFrame, ob_type: str, impulse_atr_mult: float = 1.5):
    """Return the nearest valid order block of a given type (bullish/bearish)."""
    obs = find_order_blocks(df, impulse_atr_mult)
    candidates = [ob for ob in obs if ob["type"] == ob_type]
    for ob in reversed(candidates):
        if is_order_block_valid(df, ob):
            return ob
    return None


def price_returned_to_order_block(df: pd.DataFrame, order_block: dict) -> bool:
    """
    Has the latest candle returned into the order block zone?
    Bullish: candle's low entered the zone. Bearish: candle's high entered the zone.
    """
    last = df.iloc[-1]
    if order_block["type"] == "bullish":
        return last["low"] <= order_block["high"] and last["close"] >= order_block["low"]
    else:
        return last["high"] >= order_block["low"] and last["close"] <= order_block["high"]


def is_smart_money_volume(df: pd.DataFrame, multiplier: float = 3.0) -> bool:
    """
    Smart money confirmation: is the last candle's volume at least `multiplier`
    times the previous candle's volume? (a sign of strong incoming liquidity)
    """
    if len(df) < 2:
        return False
    last_volume = df["volume"].iloc[-1]
    prev_volume = df["volume"].iloc[-2]
    if prev_volume <= 0:
        return False
    return last_volume >= multiplier * prev_volume


def detect_rsi_divergence(df: pd.DataFrame, rsi: pd.Series, lookback: int = 20):
    """
    Simple RSI divergence detection:
    - Bullish: price makes a lower low, but RSI makes a higher low
    - Bearish: price makes a higher high, but RSI makes a lower high

    Only checks the last `lookback` candles.
    """
    recent_price = df["close"].iloc[-lookback:]
    recent_rsi = rsi.iloc[-lookback:]

    price_lows = find_swing_points(recent_price, lookback=3)
    price_highs = [p for p in price_lows if p[2] == "high"]
    price_lows = [p for p in price_lows if p[2] == "low"]

    result = None

    # Bullish divergence on lows
    if len(price_lows) >= 2:
        idx1, val1, _ = price_lows[-2]
        idx2, val2, _ = price_lows[-1]
        rsi1 = recent_rsi.iloc[idx1]
        rsi2 = recent_rsi.iloc[idx2]
        if val2 < val1 and rsi2 > rsi1:
            result = {"type": "bullish_divergence", "price_low_1": val1, "price_low_2": val2,
                       "rsi_1": rsi1, "rsi_2": rsi2}

    # Bearish divergence on highs
    if len(price_highs) >= 2:
        idx1, val1, _ = price_highs[-2]
        idx2, val2, _ = price_highs[-1]
        rsi1 = recent_rsi.iloc[idx1]
        rsi2 = recent_rsi.iloc[idx2]
        if val2 > val1 and rsi2 < rsi1:
            result = {"type": "bearish_divergence", "price_high_1": val1, "price_high_2": val2,
                       "rsi_1": rsi1, "rsi_2": rsi2}

    return result
