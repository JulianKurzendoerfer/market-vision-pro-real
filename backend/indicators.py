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
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, n: int = 14, smooth_k: int = 3, smooth_d: int = 3):
    ll = low.rolling(n).min()
    hh = high.rolling(n).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    stoch_k = raw_k.rolling(smooth_k).mean()
    stoch_d = stoch_k.rolling(smooth_d).mean()
    return stoch_k, stoch_d

def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema12 = _ema(close, fast)
    ema26 = _ema(close, slow)
    mac_line = ema12 - ema26
    mac_signal = mac_line.ewm(span=signal, adjust=False).mean()
    mac_hist = mac_line - mac_signal
    return mac_line, mac_signal, mac_hist

def _bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    up = mid + k * std
    dn = mid - k * std
    return mid, up, dn

def _clean_list(s: pd.Series):
    return s.replace([np.inf, -np.inf], np.nan).where(pd.notna(s), None).tolist()

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
