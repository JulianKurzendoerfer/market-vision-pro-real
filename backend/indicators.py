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

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, n: int = 14, k: int = 3, d: int = 3):
    ll = low.rolling(n).min()
    hh = high.rolling(n).max()
    k_raw = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    k_line = k_raw.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

def _macd(close: pd.Series, f: int = 12, s: int = 26, sig: int = 9):
    fast = _ema(close, f)
    slow = _ema(close, s)
    line = fast - slow
    signal = line.ewm(span=sig, adjust=False).mean()
    hist = line - signal
    return line, signal, hist

def _bollinger(close: pd.Series, n: int = 20, mult: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std()
    up = mid + mult * std
    dn = mid - mult * std
    return mid, up, dn

def _trend_sum(close: pd.Series, n: int = 20):
    diff_sum = close.diff().rolling(n).sum()
    up = (diff_sum > 0).astype(int)
    dn = (diff_sum < 0).astype(int)
    return up, dn

def compute_indicators(df: pd.DataFrame) -> dict:
    c = df["c"]
    h = df["h"]
    l = df["l"]

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendH, trendL = _trend_sum(c, 20)

    def clean(s: pd.Series):
        return pd.Series(s, dtype="float64").replace([np.inf, -np.inf], np.nan).where(pd.notna(s), None).tolist()

    return {
        "ema20": clean(ema20),
        "ema50": clean(ema50),
        "rsi14": clean(rsi14),
        "stochK": clean(stochK),
        "stochD": clean(stochD),
        "macLine": clean(macLine),
        "macSignal": clean(macSignal),
        "macHist": clean(macHist),
        "bbMid": clean(bbMid),
        "bbUp":  clean(bbUp),
        "bbDn":  clean(bbDn),
        "trendH": clean(trendH),
        "trendL": clean(trendL),
    }
