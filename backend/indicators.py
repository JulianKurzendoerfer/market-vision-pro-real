import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int):
    return s.ewm(span=n, adjust=False).mean()

def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out

def stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series,
             n: int = 14, k_smooth: int = 3, d_smooth: int = 3):
    ll = low.rolling(n).min()
    hh = high.rolling(n).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    k = raw_k.rolling(k_smooth).mean()
    d = k.rolling(d_smooth).mean()
    return k, d

def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    line = ema_fast - ema_slow
    sig = line.ewm(span=signal, adjust=False).mean()
    hist = line - sig
    return line, sig, hist

def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    std = close.rolling(n).std(ddof=0)
    up = mid + k * std
    dn = mid - k * std
    return mid, up, dn

def compute_bundle(df: pd.DataFrame) -> dict:
    df = df.copy()
    for col in ("open","high","low","close","volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    c = df["close"]
    h = df["high"]
    l = df["low"]

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    r = rsi(c, 14)
    k, d = stoch_kd(c, h, l, 14, 3, 3)
    m_line, m_sig, m_hist = macd(c, 12, 26, 9)
    bbmid, bbup, bbdn = bollinger(c, 20, 2.0)
    trendH = h.rolling(20).max()
    trendL = l.rolling(20).min()

    def _clean(s: pd.Series):
        return s.replace([np.inf, -np.inf], np.nan).where(pd.notna(s), None).tolist()

    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi": _clean(r),
        "stochK": _clean(k),
        "stochD": _clean(d),
        "macdLine": _clean(m_line),
        "macdSignal": _clean(m_sig),
        "macdHist": _clean(m_hist),
        "bbMid": _clean(bbmid),
        "bbUp": _clean(bbup),
        "bbDn": _clean(bbdn),
        "trendH": _clean(trendH),
        "trendL": _clean(trendL),
    }
