import numpy as np
import pandas as pd

def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    a = 1.0 / n
    roll_up = up.ewm(alpha=a, adjust=False).mean()
    roll_dn = dn.ewm(alpha=a, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _stoch(close, high, low, n=14, k=3, d=3):
    ll = low.rolling(n).min()
    hh = high.rolling(n).max()
    raw_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    kline = raw_k.rolling(k).mean()
    dline = kline.rolling(d).mean()
    return kline, dline

def _bollinger(c, n=20, k=2.0):
    mid = c.rolling(n).mean()
    std = c.rolling(n).std(ddof=0)
    up = mid + k * std
    dn = mid - k * std
    return mid, up, dn

def _clean_series(s):
    return pd.Series(s, dtype="float64").replace([np.inf, -np.inf], np.nan).tolist()

def compute_indicators(df):
    c = pd.Series(df.get("c", []), dtype="float64")
    h = pd.Series(df.get("h", []), dtype="float64")
    l = pd.Series(df.get("l", []), dtype="float64")

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch(c, h, l, 14, 3, 3)
    macLine = _ema(c, 12) - _ema(c, 26)
    macSignal = macLine.ewm(span=9, adjust=False).mean()
    macHist = macLine - macSignal
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendH = h.rolling(20).max()
    trendL = l.rolling(20).min()

    return {
        "ema20": _clean_series(ema20),
        "ema50": _clean_series(ema50),
        "rsi": _clean_series(rsi14),
        "stochK": _clean_series(stochK),
        "stochD": _clean_series(stochD),
        "macLine": _clean_series(macLine),
        "macSignal": _clean_series(macSignal),
        "macHist": _clean_series(macHist),
        "bbMid": _clean_series(bbMid),
        "bbUp": _clean_series(bbUp),
        "bbDn": _clean_series(bbDn),
        "trendH": _clean_series(trendH),
        "trendL": _clean_series(trendL),
    }
