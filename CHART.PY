"""
Draw a candlestick chart with an order block zone and a stop-loss line overlay.
Output is a PNG image buffer ready to be sent to Telegram.
"""

import matplotlib
matplotlib.use("Agg")  # no display needed, just generate the file
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
import io


def plot_chart_with_zones(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    order_block: dict = None,
    stop_loss: float = None,
    title_extra: str = "",
) -> io.BytesIO:
    """
    Plot a simple candlestick chart + order block rectangle (supply/demand zone)
    + stop-loss line. Returns a BytesIO buffer containing a PNG image.
    """
    df = df.copy().reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)

    # Draw candles manually (no extra dependency needed)
    width = 0.6
    for i, row in df.iterrows():
        color = "#26a69a" if row["close"] >= row["open"] else "#ef5350"
        # wick
        ax.plot([i, i], [row["low"], row["high"]], color=color, linewidth=1)
        # body
        lower = min(row["open"], row["close"])
        height = abs(row["close"] - row["open"]) or 0.0001
        ax.add_patch(Rectangle((i - width / 2, lower), width, height, color=color))

    # Order block / supply-demand zone
    if order_block is not None:
        ob_color = "#2196f3" if order_block["type"] == "bullish" else "#ff9800"
        ob_label = f"{'Bullish' if order_block['type'] == 'bullish' else 'Bearish'} Order Block"
        ax.axhspan(order_block["low"], order_block["high"], color=ob_color, alpha=0.25, label=ob_label)

    # Stop loss line
    if stop_loss is not None:
        ax.axhline(stop_loss, color="red", linestyle="--", linewidth=1.2, label=f"Stop Loss: {stop_loss:.4f}")

    ax.set_title(f"{symbol} | {timeframe} {title_extra}", fontsize=13)
    ax.set_xlabel("Candles (most recent on the right)")
    ax.set_ylabel("Price")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_xlim(-1, len(df))
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf
