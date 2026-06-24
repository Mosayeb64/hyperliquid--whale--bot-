"""
Main bot loop: scans the market and sends Telegram notifications.

Strategy:
- Main structure/trend comes from the 1D and 4H timeframes
- Entry trigger comes from the 1H timeframe, requiring all of:
    1) RSI in the oversold zone
    2) Bullish structure break (CHoCH) on 4H
    3) Price returning into a valid bullish order block
    4) Smart money confirmation: trigger candle volume >= N times previous candle
- If all conditions are met, a stop loss (below the last 1H low) is calculated
  and a message + chart image (with order block zone and stop-loss line) is sent
"""

import asyncio
import logging
from datetime import datetime

import config
from data_feed import fetch_ohlcv, fetch_last_price, fetch_all_usdt_spot_symbols
from strategy import (
    calculate_rsi,
    detect_structure_break,
    get_nearest_valid_order_block,
    price_returned_to_order_block,
    is_smart_money_volume,
)
from chart import plot_chart_with_zones
from notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

notifier = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)

# Prevent sending duplicate signals for the same symbol/condition
_last_signals = {}


def _already_sent(symbol: str, signal_type: str, value):
    key = f"{symbol}-{signal_type}"
    return _last_signals.get(key) == value


def _mark_sent(symbol: str, signal_type: str, value):
    key = f"{symbol}-{signal_type}"
    _last_signals[key] = value


def get_symbol_list() -> list:
    if config.SCAN_ALL_USDT_PAIRS:
        try:
            symbols = fetch_all_usdt_spot_symbols()
            logger.info(f"Found {len(symbols)} USDT spot symbols to scan")
            return symbols
        except Exception as e:
            logger.error(f"Error fetching symbol list, falling back to default list: {e}")
            return config.SYMBOLS
    return config.SYMBOLS


def calculate_stop_loss(df_1h):
    """Stop loss = slightly below the lowest low in the last N 1H candles."""
    recent_low = df_1h["low"].iloc[-config.STOP_LOSS_LOOKBACK_CANDLES:].min()
    buffer = recent_low * (config.STOP_LOSS_BUFFER_PERCENT / 100)
    return recent_low - buffer


async def analyze_symbol(symbol: str):
    try:
        df_4h = fetch_ohlcv(symbol, "4h", limit=config.CANDLES_LIMIT)
        df_1h = fetch_ohlcv(symbol, config.TRIGGER_TIMEFRAME, limit=config.CANDLES_LIMIT)
    except Exception as e:
        logger.warning(f"Skipping {symbol} due to data fetch error: {e}")
        return

    min_len = config.RSI_PERIOD + config.ORDER_BLOCK_ATR_PERIOD + 5
    if len(df_4h) < min_len or len(df_1h) < min_len:
        return

    # 1) RSI oversold on the trigger timeframe (1H)
    rsi_1h = calculate_rsi(df_1h["close"], config.RSI_PERIOD)
    last_rsi = rsi_1h.iloc[-1]
    if last_rsi > config.RSI_OVERSOLD:
        return

    # 2) Bullish structure break on the 4H timeframe (main structure)
    structure = detect_structure_break(df_4h, config.SWING_LOOKBACK)
    if not structure or structure["type"] != "bullish_structure_break":
        return

    # 3) Price returning to a valid bullish order block (same 4H timeframe)
    order_block = get_nearest_valid_order_block(
        df_4h, "bullish", config.ORDER_BLOCK_IMPULSE_ATR_MULT
    )
    if not order_block:
        return
    if not price_returned_to_order_block(df_1h, order_block):
        return

    # 4) Smart money confirmation: trigger candle volume must be >= N times the previous candle
    if not is_smart_money_volume(df_1h, config.SMART_MONEY_VOLUME_MULTIPLIER):
        return

    # All conditions met -> final signal
    last_close = df_1h["close"].iloc[-1]
    signal_value = round(last_close, 6)
    if _already_sent(symbol, "buy_signal", signal_value):
        return  # this exact signal was already sent

    stop_loss = calculate_stop_loss(df_1h)

    last_volume = df_1h["volume"].iloc[-1]
    prev_volume = df_1h["volume"].iloc[-2]
    volume_ratio = last_volume / prev_volume if prev_volume else 0

    caption = (
        f"Buy signal (spot): {symbol}\n\n"
        f"RSI (1H) oversold: {last_rsi:.1f}\n"
        f"Bullish structure break on 4H\n"
        f"Price returned to a valid order block\n"
        f"Smart money confirmation: volume {volume_ratio:.1f}x previous candle\n\n"
        f"Current price: {last_close}\n"
        f"Suggested stop loss: {stop_loss:.6f}\n"
        f"Order block zone: {order_block['low']:.6f} - {order_block['high']:.6f}"
    )

    try:
        chart_buf = plot_chart_with_zones(
            df_4h.tail(60),
            symbol=symbol,
            timeframe="4H",
            order_block=order_block,
            stop_loss=stop_loss,
        )
        await notifier.send_photo(chart_buf, caption=caption)
    except Exception as e:
        logger.error(f"Error rendering/sending chart for {symbol}: {e}")
        await notifier.send(caption)  # at least send the text message

    _mark_sent(symbol, "buy_signal", signal_value)
    logger.info(f"Signal sent: {symbol}")


async def check_price_alerts():
    for alert in config.PRICE_ALERTS:
        symbol = alert["symbol"]
        target = alert["price"]
        direction = alert["direction"]
        try:
            price = fetch_last_price(symbol)
        except Exception as e:
            logger.error(f"Error fetching live price for {symbol}: {e}")
            continue

        triggered = (direction == "above" and price >= target) or (
            direction == "below" and price <= target
        )
        if triggered:
            key = f"price_alert-{symbol}-{target}-{direction}"
            if _last_signals.get(key) != True:
                await notifier.send(
                    f"Price alert: {symbol}\n"
                    f"Target: {target} ({'above' if direction == 'above' else 'below'})\n"
                    f"Current price: {price}"
                )
                _last_signals[key] = True


async def run_full_scan():
    symbols = get_symbol_list()
    logger.info(f"Starting scan of {len(symbols)} symbols...")

    for symbol in symbols:
        await analyze_symbol(symbol)
        await asyncio.sleep(0.3)  # small delay between requests to respect Binance rate limits

    await check_price_alerts()
    logger.info("Full market scan complete.")


async def main_loop():
    logger.info("Trading bot started.")
    await notifier.send("Trading bot is active and scanning the Binance spot market.")

    while True:
        start = datetime.now()
        try:
            await run_full_scan()
        except Exception as e:
            logger.error(f"General error during scan: {e}")

        elapsed = (datetime.now() - start).total_seconds()
        logger.info(f"This scan took {elapsed:.1f} seconds")
        sleep_time = max(5, config.CHECK_INTERVAL_SECONDS - elapsed)
        await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    asyncio.run(main_loop())
