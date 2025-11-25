import pandas as pd, numpy as np

def ema(s, n): 
    return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = -d.clip(upper=0.0)
    au = up.ewm(alpha=1/n, adjust=False).mean()
    ad = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd_w(close, fast=12, slow=26, signal=9):
    f = close.ewm(span=fast, adjust=False).mean()
    s = close.ewm(span=slow, adjust=False).mean()
    m = f - s
    sig = m.ewm(span=signal, adjust=False).mean()
    hist = m - sig
    return m, sig, hist

def true_range(h, l, c):
    return pd.concat([h-l, (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)

def atr(h, l, c, n=20):
    tr = true_range(h, l, c)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def stoch_rsi(close, rsi_len=14, stoch_len=14, k=3, d=3):
    r = rsi_wilder(close, rsi_len)
    rmin = r.rolling(stoch_len).min()
    rmax = r.rolling(stoch_len).max()
    sr = 100 * (r - rmin) / (rmax - rmin)
    kf = sr.rolling(k).mean()
    df = kf.rolling(d).mean()
    return kf, df

def compute_indicators(df):
    out = pd.DataFrame(index=df.index)
    c = df["Close"]; h = df["High"]; l = df["Low"]
    out["RSI"] = rsi_wilder(c, 14)
    m, s, hist = macd_w(c, 12, 26, 9)
    out["MACD"] = m; out["MACD_signal"] = s; out["MACD_hist"] = hist
    kf, df_ = stoch_rsi(c, 14, 14, 3, 3)
    out["ST_RSI_K"] = kf; out["ST_RSI_D"] = df_
    a = atr(h, l, c, 20)
    out["ATR20"] = a
    basis = ema(c, 20)
    out["KC_basis"] = basis
    out["KC_upper"] = basis + 2*a
    out["KC_lower"] = basis - 2*a
    return out
