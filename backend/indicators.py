import numpy as np
import pandas as pd

def _clean_series(s: pd.Series):
    return [None if (pd.isna(x) or np.isinf(x)) else float(x) for x in s]

def _ema(s: pd.Series, n: int):
    return s.ewm(span=n, adjust=False).mean()

def rsi(close: pd.Series, n: int = 14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out

def stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, n: int = 14, s: int = 3, d: int = 3):
    ll = low.rolling(n).min()
    hh = high.rolling(n).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    k = raw_k.rolling(s).mean()
    dd = k.rolling(d).mean()
    return k, dd

def macd(close: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    line = ema_fast - ema_slow
    signal = line.ewm(span=sig, adjust=False).mean()
    hist = line - signal
    return line, signal, hist

def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    up = mid + k*std
    dn = mid - k*std
    return mid, up, dn

def compute(df: pd.DataFrame):
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)

    rsi14 = rsi(c, 14)

    stochK, stochD = stoch_kd(c, h, l, 14, 3, 3)

    macLine, macSignal, macHist = macd(c, 12, 26, 9)

    bbMid, bbUp, bbDn = bollinger(c, 20, 2.0)

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

def compute_bundle(df: pd.DataFrame):
    inds = compute(df)
    out = {
        "t": [int(x) if pd.notna(x) else None for x in df["t"]],
        "o": _clean_series(df["open"]),
        "h": _clean_series(df["high"]),
        "l": _clean_series(df["low"]),
        "c": _clean_series(df["close"]),
        "v": _clean_series(df["volume"]),
        "indicators": inds,
    }
    return out
