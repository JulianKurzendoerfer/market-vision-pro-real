import numpy as np
import pandas as pd

def _clean(series, nd=2):
    s = pd.Series(series, dtype="float64").replace([np.inf, -np.inf], np.nan)
    out = []
    for v in s:
        if pd.isna(v):
            out.append(None)
        else:
            out.append(round(float(v), nd))
    return out

def _rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    r = 100 - 100/(1+rs)
    return r

def compute(df):
    df = df.copy()
    c = df["close"].astype("float64")
    h = df["high"].astype("float64")
    l = df["low"].astype("float64")

    ema20 = c.ewm(span=20, adjust=False).mean()
    ema50 = c.ewm(span=50, adjust=False).mean()

    rsi14 = _rsi(c, 14)

    n = 14
    ll = l.rolling(n).min()
    hh = h.rolling(n).max()
    k = (c - ll) * 100.0 / (hh - ll)
    d = k.rolling(3).mean()

    macd_line = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    th = h.rolling(20).max()
    tl = l.rolling(20).min()

    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi": _clean(rsi14),
        "stochK": _clean(k),
        "stochD": _clean(d),
        "macdLine": _clean(macd_line),
        "macdSignal": _clean(macd_signal),
        "macdHist": _clean(macd_hist),
        "trendH": _clean(th),
        "trendL": _clean(tl),
    }
