import asyncio
import aiohttp
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
WHALE_WALLETS = os.environ.get("WALLETS", "")
WHALE_MIN_SIZE = float(os.environ.get("MIN_SIZE", "50000"))
SPIKE_MULTIPLIER = float(os.environ.get("SPIKE_MULTIPLIER", "5"))
RSI_TIMEFRAME = os.environ.get("RSI_TIMEFRAME", "1d")
RSI_OVERSOLD = float(os.environ.get("RSI_OVERSOLD", "30"))
RSI_OVERBOUGHT = float(os.environ.get("RSI_OVERBOUGHT", "70"))

VOLUME_ALERTED = set()
RSI_ALERTED = set()
WHALE_LAST_DATA = {}

async def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        await session.post(url, json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"})

async def get_wallet_positions(address):
    url = "https://api.hyperliquid.xyz/info"
    body = {"type": "clearinghouseState", "user": address}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body) as r:
            return await r.json()

async def check_whales():
    if not WHALE_WALLETS:
        return
    wallet_list = [w.strip() for w in WHALE_WALLETS.split(",") if w.strip()]
    for address in wallet_list:
        try:
            data = await get_wallet_positions(address)
            positions = data.get("assetPositions", [])
            label = address[:8] + "..."
            for pos in positions:
                p = pos.get("position", {})
                coin = p.get("coin", "")
                size = float(p.get("szi", 0))
                entry = float(p.get("entryPx", 0) or 0)
                notional = abs(size) * entry
                leverage = p.get("leverage", {}).get("value", 1)
                liq_px = p.get("liquidationPx", 0)
                if notional < WHALE_MIN_SIZE:
                    continue
                key = f"{address}_{coin}"
                prev = WHALE_LAST_DATA.get(key)
                direction = "🟢 Long" if size > 0 else "🔴 Short"
                change = ""
                if prev:
                    prev_size = prev.get("size", 0)
                    if abs(size) > abs(prev_size):
                        change = "Increased"
                    elif abs(size) < abs(prev_size):
                        change = "Decreased"
                    else:
                        WHALE_LAST_DATA[key] = {"size": size, "entry": entry}
                        continue
                else:
                    change = "New Position"
                now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                msg = (
                    f"🐋 <b>#HyperLiquid Whale</b>\n\n"
                    f"• Label: {label}\n"
                    f"• {change}\n\n"
                    f"Coin: <b>{coin}/USDT</b>\n"
                    f"• {direction} Position\n\n"
                    f"Address: <code>{address}</code>\n"
                    f"• Size: {abs(size):.6f}\n"
                    f"• Entry Price: ${entry:,.2f}\n"
                    f"• Notional: ${notional:,.2f}\n"
                    f"• Leverage: {leverage}x\n"
                    f"• Liquidation Price: {liq_px}\n\n"
                    f"Last Update: {now}"
                )
                await send_telegram(msg)
                WHALE_LAST_DATA[key] = {"size": size, "entry": entry}
        except Exception as e:
            print(f"Whale error {address}: {e}")

async def get_top_symbols():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            data = await r.json()
            if not isinstance(data, list):
                return []
            usdt_pairs = [d for d in data if isinstance(d, dict) and d.get("symbol", "").endswith("USDT")]
            sorted_pairs = sorted(usdt_pairs, key=lambda x: float(x.get("quoteVolume", 0)), reverse=True)
            return [d["symbol"] for d in sorted_pairs[:50]]

async def get_klines(symbol, interval="1h", limit=32):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            data = await r.json()
            if not isinstance(data, list):
                return []
            return data

async def check_volume_spikes():
    global VOLUME_ALERTED
    new_alerted = set()
    try:
        symbols = await get_top_symbols()
        if not symbols:
            return
    except Exception as e:
        print(f"Volume error: {e}")
        return
    for symbol in symbols:
        try:
            klines = await get_klines(symbol)
            if len(klines) < 31:
                continue
            volumes = [float(k[5]) for k in klines[:-1]]
            current_volume = float(klines[-1][5])
            current_price = float(klines[-1][4])
            avg_volume = sum(volumes[-30:]) / 30
            if avg_volume == 0:
                continue
            ratio = current_volume / avg_volume
            if ratio >= SPIKE_MULTIPLIER:
                new_alerted.add(symbol)
                if symbol not in VOLUME_ALERTED:
                    open_price = float(klines[-1][1])
                    change = ((current_price - open_price) / open_price) * 100
                    direction = "📈" if change >= 0 else "📉"
                    now = datetime.now().strftime("%d/%m/%Y %H:%M")
                    msg = (
                        f"🚨 <b>Volume Spike Detected!</b>\n\n"
                        f"Coin: <b>{symbol}</b>\n"
                        f"Current Volume: {current_volume:,.0f}\n"
                        f"Average Volume (30h): {avg_volume:,.0f}\n"
                        f"Ratio: <b>{ratio:.1f}x</b> 🔥\n\n"
                        f"Price: ${current_price:,.4f}\n"
                        f"Change: {direction} {change:+.2f}%\n\n"
                        f"Time: {now}"
                    )
                    await send_telegram(msg)
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Volume spike error {symbol}: {e}")
    VOLUME_ALERTED = new_alerted

def calculate_rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i-1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    if len(gains) < period:
        return 50
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def is_doji(open_p, high_p, low_p, close_p):
    body = abs(close_p - open_p)
    total_range = high_p - low_p
    if total_range == 0:
        return False
    return (body / total_range) < 0.1

async def check_rsi_doji():
    global RSI_ALERTED
    new_alerted = set()
    try:
        symbols = await get_top_symbols()
        if not symbols:
            return
    except Exception as e:
        print(f"RSI error: {e}")
        return
    tf_label = "Weekly" if RSI_TIMEFRAME == "1w" else "Daily"
    for symbol in symbols:
        try:
            klines = await get_klines(symbol, interval=RSI_TIMEFRAME, limit=50)
            if len(klines) < 20:
                continue
            closes = [float(k[4]) for k in klines]
            last = klines[-2]
            open_p = float(last[1])
            high_p = float(last[2])
            low_p = float(last[3])
            close_p = float(last[4])
            rsi = calculate_rsi(closes[:-1])
            doji = is_doji(open_p, high_p, low_p, close_p)
            if not doji:
                continue
            signal = ""
            emoji = ""
            if rsi <= RSI_OVERSOLD:
                signal = "BUY"
                emoji = "🟢"
            elif rsi >= RSI_OVERBOUGHT:
                signal = "SELL"
                emoji = "🔴"
            else:
                continue
            key = f"{symbol}_{RSI_TIMEFRAME}_{signal}"
            new_alerted.add(key)
            if key not in RSI_ALERTED:
                now = datetime.now().strftime("%d/%m/%Y %H:%M")
                msg = (
                    f"🎯 <b>RSI + Doji Signal!</b>\n\n"
                    f"Coin: <b>{symbol}</b>\n"
                    f"Signal: {emoji} <b>{signal}</b>\n\n"
                    f"RSI: <b>{rsi:.1f}</b> ({'Oversold' if signal == 'BUY' else 'Overbought'})\n"
                    f"Doji: ✅ Confirmed\n\n"
                    f"Price: ${close_p:,.4f}\n"
                    f"Timeframe: {tf_label}\n\n"
                    f"Time: {now}"
                )
                await send_telegram(msg)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"RSI doji error {symbol}: {e}")
    RSI_ALERTED = new_alerted

async def main():
    print("All Bots Started!")
    await send_telegram(
        "🤖 <b>All Bots Started!</b>\n\n"
        "🐋 HyperLiquid Whale Tracker\n"
        "🚨 Volume Spike Detector\n"
        "🎯 RSI + Doji Signal (Daily/Weekly)\n\n"
        "All systems running!"
    )
    while True:
        now = datetime.now()
        print(f"Running... {now}")
        await check_whales()
        await asyncio.sleep(2)
        await check_volume_spikes()
        await asyncio.sleep(2)
        if now.hour % 6 == 0 and now.minute < 1:
            await check_rsi_doji()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
