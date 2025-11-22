import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / (roll_dn.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def _stoch_kd(c: pd.Series, h: pd.Series, l: pd.Series, n: int = 14, k: int = 3, d: int = 3):
    hh = h.rolling(n).max()
    ll = l.rolling(n).min()
    raw_k = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    k_fast = raw_k.rolling(k).mean()
    d_slow = k_fast.rolling(d).mean()
    return k_fast.fillna(50), d_slow.fillna(50)

def _macd(c: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    ema_fast = _ema(c, fast)
    ema_slow = _ema(c, slow)
    line = ema_fast - ema_slow
    signal = line.ewm(span=sig, adjust=False).mean()
    hist = line - signal
    return line, signal, hist

def _bollinger(c: pd.Series, n: int = 20, k: float = 2.0):
    mid = c.rolling(n).mean()
    sd = c.rolling(n).std(ddof=0)
    up = mid + k*sd
    dn = mid - k*sd
    return mid, up, dn

def _trend_flags(c: pd.Series, n:int=20):
    hi = c > c.rolling(n).max().shift(1)
    lo = c < c.rolling(n).min().shift(1)
    return hi.fillna(False).astype(int), lo.fillna(False).astype(int)

def compute_indicators(df: pd.DataFrame) -> dict:
    c = df['c']
    h = df['h']
    l = df['l']
    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendH, trendL = _trend_flags(c, 20)

    def _clean(s: pd.Series): 
        return pd.Series(s, dtype='float64').replace([np.inf, -np.inf], np.nan).fillna(method='ffill').fillna(method='bfill').fillna(0).tolist()

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
