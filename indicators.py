import numpy as np
import pandas as pd

def _clean(s: pd.Series):
    x = s.astype("float64").replace([np.inf, -np.inf], np.nan)
    x = x.round(6)
    return [None if pd.isna(v) else float(v) for v in x.to_numpy()]

def _ema(c: pd.Series, n: int):
    return c.ewm(span=n, adjust=False).mean()

def _rsi(c: pd.Series, n: int = 14):
    d = c.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_dn
    return 100 - (100 / (1 + rs))

def _stoch_kd(h: pd.Series, l: pd.Series, c: pd.Series, k: int = 14, smooth: int = 3, d: int = 3):
    ll = l.rolling(k).min()
    hh = h.rolling(k).max()
    rawk = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    ksm = rawk.rolling(smooth).mean()
    dsm = ksm.rolling(d).mean()
    return ksm, dsm

def _macd(c: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    emaf = _ema(c, fast)
    emas = _ema(c, slow)
    line = emaf - emas
    sig = line.ewm(span=signal, adjust=False).mean()
    hist = line - sig
    return line, sig, hist

def _bollinger(c: pd.Series, n: int = 20, k: float = 2.0):
    mid = c.rolling(n).mean()
    std = c.rolling(n).std()
    up = mid + k * std
    dn = mid - k * std
    return mid, up, dn

def compute_indicators(df: pd.DataFrame) -> dict:
    c = pd.Series(df["c"], dtype="float64")
    h = pd.Series(df["h"], dtype="float64")
    l = pd.Series(df["l"], dtype="float64")

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(h, l, c, 14, 3, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendH = h.rolling(20).max()
    trendL = l.rolling(20).min()

    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi": _clean(rsi14),
        "stochK": _clean(stochK),
        "stochD": _clean(stochD),
        "macLine": _clean(macLine),
        "macSignal": _clean(macSignal),
        "macHist": _clean(macHist),
        "bbMid": _clean(bbMid),
        "bbUp": _clean(bbUp),
        "bbDn": _clean(bbDn),
        "trendH": _clean(trendH),
        "trendL": _clean(trendL),
    }
