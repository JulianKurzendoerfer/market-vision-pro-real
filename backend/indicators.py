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
    raw_k = 100 * (close - ll) / (hh - ll)
    k_line = raw_k.rolling(k).mean()
    d_line = k_line.rolling(d).mean()
    return k_line, d_line

def _macd(close: pd.Series, f: int = 12, s: int = 26, sig: int = 9):
    mac = _ema(close, f) - _ema(close, s)
    signal = _ema(mac, sig)
    hist = mac - signal
    return mac, signal, hist

def _bollinger(close: pd.Series, n: int = 20, z: float = 2.0):
    ma = close.rolling(n).mean()
    sd = close.rolling(n).std()
    up = ma + z * sd
    dn = ma - z * sd
    return ma, up, dn

def _clean(x: pd.Series):
    return x.astype("float64").where(pd.notna(x), None).tolist()

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
    trendH = h.rolling(20).max()
    trendL = l.rolling(20).min()

    out = {
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
    return out
