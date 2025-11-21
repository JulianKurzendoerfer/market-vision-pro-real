import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int):
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close: pd.Series, n: int = 14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    alpha = 1.0 / n
    roll_up = up.ewm(alpha=alpha, adjust=False).mean()
    roll_dn = dn.ewm(alpha=alpha, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, k: int = 14, d: int = 3, smooth: int = 3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    stochK = raw_k.rolling(smooth).mean()
    stochD = stochK.rolling(d).mean()
    return stochK, stochD

def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macLine = ema_fast - ema_slow
    macSignal = macLine.ewm(span=signal, adjust=False).mean()
    macHist = macLine - macSignal
    return macLine, macSignal, macHist

def _bollinger(close: pd.Series, n: int = 20, mult: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    up = mid + mult * std
    dn = mid - mult * std
    return mid, up, dn

def _clean(x: pd.Series) -> list:
    a = pd.to_numeric(x, errors="coerce").astype(float)
    a = a.replace([np.inf, -np.inf], np.nan)
    return a.where(pd.notna(a), None).tolist()

def compute(df: pd.DataFrame) -> dict:
    df = df.copy()
    for c in ("t","open","high","low","close","volume"):
        if c not in df.columns: df[c]=np.nan
    c = pd.to_numeric(df["close"], errors="coerce")
    h = pd.to_numeric(df["high"], errors="coerce")
    l = pd.to_numeric(df["low"], errors="coerce")

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3, 3)
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
