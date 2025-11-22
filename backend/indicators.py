import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, n: int = 14, smooth: int = 3):
    ll = low.rolling(n).min()
    hh = high.rolling(n).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    stochK = raw_k.rolling(smooth).mean()
    stochD = stochK.rolling(smooth).mean()
    return stochK, stochD

def _macd(close: pd.Series, fast: int = 12, slow: int = 26, sig: int = 9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macLine = ema_fast - ema_slow
    macSignal = macLine.ewm(span=sig, adjust=False).mean()
    macHist = macLine - macSignal
    return macLine, macSignal, macHist

def _bollinger(close: pd.Series, n: int = 20, dev: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    bbu = mid + dev * std
    bbd = mid - dev * std
    return mid, bbu, bbd

def _trend_high_low(high: pd.Series, low: pd.Series, n: int = 20):
    trendH = high.rolling(n).max()
    trendL = low.rolling(n).min()
    return trendH, trendL

def _clean_list(s: pd.Series):
    a = s.astype("float64").to_numpy()
    a[~np.isfinite(a)] = np.nan
    return [None if np.isnan(x) else float(x) for x in a]

def compute_indicators(df: pd.DataFrame) -> dict:
    c = pd.to_numeric(df["c"], errors="coerce")
    h = pd.to_numeric(df["h"], errors="coerce")
    l = pd.to_numeric(df["l"], errors="coerce")

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendH, trendL = _trend_high_low(h, l, 20)

    return {
        "ema20": _clean_list(ema20),
        "ema50": _clean_list(ema50),
        "rsi": _clean_list(rsi14),
        "stochK": _clean_list(stochK),
        "stochD": _clean_list(stochD),
        "macLine": _clean_list(macLine),
        "macSignal": _clean_list(macSignal),
        "macHist": _clean_list(macHist),
        "bbMid": _clean_list(bbMid),
        "bbUp": _clean_list(bbUp),
        "bbDn": _clean_list(bbDn),
        "trendH": _clean_list(trendH),
        "trendL": _clean_list(trendL),
    }
