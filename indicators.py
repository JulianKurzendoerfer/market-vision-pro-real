import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int):
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close: pd.Series, n: int = 14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, k: int = 14, smooth: int = 3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    stochK = raw_k.rolling(smooth).mean()
    stochD = stochK.rolling(smooth).mean()
    return stochK, stochD

def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    macLine = ema_f - ema_s
    macSignal = macLine.ewm(span=signal, adjust=False).mean()
    macHist = macLine - macSignal
    return macLine, macSignal, macHist

def _bollinger(close: pd.Series, n: int = 20, dev: float = 2.0):
    m = close.rolling(n).mean()
    s = close.rolling(n).std(ddof=0)
    bbMd = m
    bbUp = m + dev * s
    bbDn = m - dev * s
    return bbMd, bbUp, bbDn

def _clean_series(s: pd.Series):
    return [None if pd.isna(x) or np.isinf(x) else float(x) for x in s.to_numpy()]

def compute_indicators(df: pd.DataFrame) -> dict:
    c = pd.to_numeric(df["c"], errors="coerce")
    h = pd.to_numeric(df["h"], errors="coerce")
    l = pd.to_numeric(df["l"], errors="coerce")
    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMd, bbUp, bbDn = _bollinger(c, 20, 2.0)
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
        "bbMd": _clean_series(bbMd),
        "bbUp": _clean_series(bbUp),
        "bbDn": _clean_series(bbDn),
        "trendH": _clean_series(trendH),
        "trendL": _clean_series(trendL)
    }
