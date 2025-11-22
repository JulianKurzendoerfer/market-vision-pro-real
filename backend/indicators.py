import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    ru = up.ewm(alpha=1/n, adjust=False).mean()
    rd = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = ru / rd.replace(0, np.nan)
    return 100 - (100/(1+rs))

def _stoch_kd(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14, k: int = 3, d: int = 3):
    ll = l.rolling(n).min()
    hh = h.rolling(n).max()
    kv = (c - ll) / (hh - ll).replace(0, np.nan) * 100
    kv = kv.clip(0, 100)
    dv = kv.rolling(d).mean()
    kv = kv.rolling(k).mean()
    return kv, dv

def _macd(c: pd.Series, f: int = 12, s: int = 26, sig: int = 9):
    line = _ema(c, f) - _ema(c, s)
    signal = line.ewm(span=sig, adjust=False).mean()
    hist = line - signal
    return line, signal, hist

def _boll(c: pd.Series, n: int = 20, m: float = 2.0):
    mid = c.rolling(n).mean()
    std = c.rolling(n).std()
    up = mid + m*std
    dn = mid - m*std
    return mid, up, dn

def _trend_hl(h: pd.Series, l: pd.Series, n: int = 20):
    th = h.rolling(n).max()
    tl = l.rolling(n).min()
    return th, tl

def _clean(s: pd.Series) -> list:
    return s.astype("float64").replace([np.inf, -np.inf], np.nan).where(~s.isna(), np.nan).replace({np.nan: None}).tolist()

def compute_indicators(df: pd.DataFrame) -> dict:
    c = df["c"]
    h = df["h"]
    l = df["l"]
    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(h, l, c, 14, 3, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _boll(c, 20, 2.0)
    trendH, trendL = _trend_hl(h, l, 20)
    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi14": _clean(rsi14),
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
