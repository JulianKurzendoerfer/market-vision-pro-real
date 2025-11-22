import numpy as np
import pandas as pd

def ema(series, n):
    return series.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, p=14):
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/p, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/p, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.NAN)
    rsi = 100 - (100 / (1 + rs))
    return rsi.clip(0, 100)

def macd_tv(close, fast=12, slow=26, signal=9):
    macd_line = ema(close, fast) - ema(close, slow)
    macd_signal = ema(macd_line, signal)
    macd_hist = macd_line - macd_signal

    th = h.rolling(20).max()
    tl = l.rolling(20).min()

    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi": _clean(rsi14),
        "stochK": _clean(k),
        "stochD": _clean(d),
        "macdLine": _clean(macd_line),
        "macdSignal": _clean(macd_signal),
        "macdHist": _clean(macd_hist),
        "trend": _clean(th),
        "trendL": _clean(tl),
    }
