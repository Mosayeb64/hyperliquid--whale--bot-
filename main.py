import asyncio
import aiohttp
import json
import os
from datetime import datetime

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
MIN_SIZE = float(os.environ.get("MIN_SIZE", "50000"))

LAST_DATA = {}

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

async def check_wallets():
    wallets_str = os.environ.get("WALLETS", "")
    if not wallets_str:
        return
    wallet_list = [w.strip() for w in wallets_str.split(",") if w.strip()]
    
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
                
                if notional < MIN_SIZE:
                    continue
                
                key = f"{address}_{coin}"
                prev = LAST_DATA.get(key)
                
                direction = "🟢 Long" if size > 0 else "🔴 Short"
                change = ""
                
                if prev:
                    prev_size = prev.get("size", 0)
                    if abs(size) > abs(prev_size):
                        change = "Increased"
                    elif abs(size) < abs(prev_size):
                        change = "Decreased"
                    else:
                        LAST_DATA[key] = {"size": size, "entry": entry}
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
                    f"🕐 Last Update: {now}"
                )
                await send_telegram(msg)
                LAST_DATA[key] = {"size": size, "entry": entry}
                
        except Exception as e:
            print(f"Error checking {address}: {e}")

async def main():
    print("Whale Tracker Bot Started!")
    await send_telegram("🐋 Whale Tracker Bot Started Successfully!")
    while True:
        await check_wallets()
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
