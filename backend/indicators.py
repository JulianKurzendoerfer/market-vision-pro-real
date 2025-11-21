import numpy as np, pandas as pd

def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    rs = up / dn
    return 100 - (100/(1+rs))

def stoch(high, low, close, k=14, d=3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    kraw = (close - ll) / (hh - ll) * 100
    ks = kraw.rolling(d).mean()
    ds = ks.rolling(d).mean()
    return ks, ds

def macd(close, f=12, s=26, sig=9):
    fast = _ema(close, f)
    slow = _ema(close, s)
    line = fast - slow
    signal = _ema(line, sig)
    hist = line - signal
    return line, signal, hist

def emas(close):
    return _ema(close, 20), _ema(close, 50)

def trend_hilo(high, low, n=50):
    th = high.rolling(n).max()
    tl = low.rolling(n).min()
    return th, tl

def compute(df):
    c = df['close'].astype(float)
    h = df['high'].astype(float)
    l = df['low'].astype(float)
    e20, e50 = emas(c)
    r = rsi(c, 14)
    k, d = stoch(h, l, c, 14, 3)
    ml, ms, mh = macd(c, 12, 26, 9)
    th, tl = trend_hilo(h, l, 50)
    out = {
        'rsi': r.tolist(),
        'stochK': k.tolist(),
        'stochD': d.tolist(),
        'macdLine': ml.tolist(),
        'macdSignal': ms.tolist(),
        'macdHist': mh.tolist(),
        'ema20': e20.tolist(),
        'ema50': e50.tolist(),
        'th': th.tolist(),
        'tl': tl.tolist(),
    }
    return out
