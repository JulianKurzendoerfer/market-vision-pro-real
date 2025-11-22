import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()

def _bbands(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = _sma(close, n)
    std = close.rolling(n).std(ddof=0)
    lo = mid - k * std
    up = mid + k * std
    return lo, mid, up

def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1 / n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _stoch(close: pd.Series, high: pd.Series, low: pd.Series, k: int = 14, d: int = 3, smooth: int = 3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw = 100 * (close - ll) / (hh - ll)
    kline = raw.rolling(smooth).mean()
    dline = kline.rolling(d).mean()
    return kline, dline

def _clean(s: pd.Series):
    out = []
    a = s.to_numpy(dtype=float, copy=False)
    for x in a:
        if x is None or np.isnan(x) or np.isinf(x):
            out.append(None)
        else:
            out.append(float(x))
    return out

def compute_indicators(df: pd.DataFrame) -> dict:
    c = df["c"]
    h = df["h"]
    l = df["l"]
    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch(c, h, l, 14, 3, 3)
    ema12 = _ema(c, 12)
    ema26 = _ema(c, 26)
    macLine = ema12 - ema26
    macSignal = macLine.ewm(span=9, adjust=False).mean()
    macHist = macLine - macSignal
    bbDn, bbMd, bbUp = _bbands(c, 20, 2.0)
    trendH = c.rolling(20).max()
    trendL = c.rolling(20).min()
    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi": _clean(rsi14),
        "stochK": _clean(stochK),
        "stochD": _clean(stochD),
        "macLine": _clean(macLine),
        "macSignal": _clean(macSignal),
        "macHist": _clean(macHist),
        "bbMd": _clean(bbMd),
        "bbUp": _clean(bbUp),
        "bbDn": _clean(bbDn),
        "trendH": _clean(trendH),
        "trendL": _clean(trendL),
    }
