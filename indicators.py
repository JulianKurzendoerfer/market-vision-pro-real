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

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, k: int = 14, d: int = 3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    stochK = raw_k
    stochD = stochK.rolling(d).mean()
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

def _clean_list(v):
    out = []
    for x in v:
        if x is None:
            out.append(None)
        else:
            try:
                if np.isinf(x) or np.isnan(x):
                    out.append(None)
                else:
                    out.append(float(x))
            except Exception:
                out.append(None)
    return out

def _clean_series(s: pd.Series):
    return _clean_list(s.replace([np.inf, -np.inf], np.nan).astype(float).tolist())

def compute_indicators(df: pd.DataFrame) -> dict:
    c = df["c"]
    h = df["h"]
    l = df["l"]

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3)
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
