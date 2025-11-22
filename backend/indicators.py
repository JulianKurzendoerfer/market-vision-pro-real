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

def _stoch_kd(close, high, low, k=14, d=3):
    ll = low.rolling(k, min_periods=1).min()
    hh = high.rolling(k, min_periods=1).max()
    raw_k = 100 * (close - ll) / (hh - ll).replace(0, np.nan)
    stoch_k = raw_k.rolling(d, min_periods=1).mean()
    stoch_d = stoch_k.rolling(d, min_periods=1).mean()
    return stoch_k, stoch_d

def _macd(close, fast=12, slow=26, signal=9):
    mac_line = _ema(close, fast) - _ema(close, slow)
    mac_sig = mac_line.ewm(span=signal, adjust=False).mean()
    mac_hist = mac_line - mac_sig
    return mac_line, mac_sig, mac_hist

def _bollinger(close, n=20, k=2.0):
    ma = close.rolling(n, min_periods=1).mean()
    std = close.rolling(n, min_periods=1).std(ddof=0)
    bb_up = ma + k*std
    bb_dn = ma - k*std
    return ma, bb_up, bb_dn

def _clean_series(s: pd.Series) -> list:
    return pd.Series(s, dtype="float64").replace([np.inf, -np.inf], np.nan).tolist()

def compute_indicators(df: pd.DataFrame) -> dict:
    c = pd.Series(df["c"])
    h = pd.Series(df["h"])
    l = pd.Series(df["l"])
    v = pd.Series(df["v"])

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendH = h.rolling(20, min_periods=1).max()
    trendL = l.rolling(20, min_periods=1).min()

    return {
        "ema20": _clean_series(ema20),
        "ema50": _clean_series(ema50),
        "rsi14": _clean_series(rsi14),
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
