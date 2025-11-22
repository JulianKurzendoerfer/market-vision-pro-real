import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _stoch(c: pd.Series, h: pd.Series, l: pd.Series, n: int = 14, m: int = 3) -> tuple[pd.Series, pd.Series]:
    ll = l.rolling(n, min_periods=1).min()
    hh = h.rolling(n, min_periods=1).max()
    k = (c - ll) / (hh - ll).replace(0, np.nan) * 100
    d = k.rolling(m, min_periods=1).mean()
    return k, d

def _macd(c: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    mac = _ema(c, fast) - _ema(c, slow)
    sigl = mac.ewm(span=sig, adjust=False).mean()
    hist = mac - sigl
    return mac, sigl, hist

def _bollinger(c: pd.Series, n: int = 20, z: float = 2.0):
    ma = c.rolling(n, min_periods=1).mean()
    sd = c.rolling(n, min_periods=1).std(ddof=0)
    up = ma + z * sd
    dn = ma - z * sd
    return ma, up, dn

def _clean_list(s: pd.Series) -> list:
    return [None if pd.isna(x) else float(x) for x in s]

def compute_indicators(df: pd.DataFrame) -> dict:
    c, h, l, v = df["c"], df["h"], df["l"], df.get("v", pd.Series(index=df.index, dtype="float64"))

    ema20  = _ema(c, 20)
    ema50  = _ema(c, 50)
    rsi14  = _rsi(c, 14)
    stochK, stochD = _stoch(c, h, l, 14, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2)

    trendH = (h >= h.rolling(20, min_periods=1).max()).astype(int)
    trendL = (l <= l.rolling(20, min_periods=1).min()).astype(int)

    out = {
        "ema20":  _clean_list(ema20),
        "ema50":  _clean_list(ema50),
        "rsi14":  _clean_list(rsi14),
        "stochK": _clean_list(stochK),
        "stochD": _clean_list(stochD),
        "macLine":   _clean_list(macLine),
        "macSignal": _clean_list(macSignal),
        "macHist":   _clean_list(macHist),
        "bbMid": _clean_list(bbMid),
        "bbUp":  _clean_list(bbUp),
        "bbDn":  _clean_list(bbDn),
        "trendH": _clean_list(trendH),
        "trendL": _clean_list(trendL),
    }
    return out
