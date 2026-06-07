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
