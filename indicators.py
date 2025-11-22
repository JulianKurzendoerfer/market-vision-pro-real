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

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, n: int = 14, smooth_k: int = 3, smooth_d: int = 3):
    ll = low.rolling(n).min()
    hh = high.rolling(n).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    stochK = raw_k.rolling(smooth_k).mean()
    stochD = stochK.rolling(smooth_d).mean()
    return stochK, stochD

def _macd(close: pd.Series, f: int = 12, s: int = 26, sig: int = 9):
    ema_f = _ema(close, f)
    ema_s = _ema(close, s)
    macLine = ema_f - ema_s
    macSignal = macLine.ewm(span=sig, adjust=False).mean()
    macHist = macLine - macSignal
    return macLine, macSignal, macHist

def _bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    up = mid + k * std
    dn = mid - k * std
    return mid, up, dn

def _clean_series(s: pd.Series) -> list:
    a = s.to_numpy(dtype="float64", copy=False)
    a[~np.isfinite(a)] = np.nan
    return pd.Series(a, dtype="float64").where(pd.notna(a), None).tolist()

def compute_indicators(df: pd.DataFrame) -> dict:
    c = pd.Series(df["c"], dtype="float64")
    h = pd.Series(df["h"], dtype="float64")
    l = pd.Series(df["l"], dtype="float64")

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)

    rsi14 = _rsi(c, 14)

    stochK, stochD = _stoch_kd(c, h, l, 14, 3, 3)

    macLine, macSignal, macHist = _macd(c, 12, 26, 9)

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
