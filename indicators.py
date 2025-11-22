import numpy as np
import pandas as pd

def ema(s, n): return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    ag = up.ewm(alpha=1/n, adjust=False).mean()
    al = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = ag / al.replace(0, np.nan)
    r = 100 - (100 / (1 + rs))
    return r.clip(0, 100)

def macd_tv(close, fast=12, slow=26, signal=9):
    m = ema(close, fast) - ema(close, slow)
    s = ema(m, signal)
    h = m - s
    return m, s, h

def atr(h, l, c, n=20):
    pc = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean()

def stochastic_full(h, l, c, k_period=14, k_smooth=3, d_period=3):
    hh = h.rolling(k_period, min_periods=k_period).max()
    ll = l.rolling(k_period, min_periods=k_period).min()
    denom = (hh - ll).replace(0, np.nan)
    rk = 100 * (c - ll) / denom
    ks = rk.rolling(k_smooth, min_periods=k_smooth).mean()
    ds = ks.rolling(d_period, min_periods=d_period).mean()
    return ks.clip(0, 100), ds.clip(0, 100)

def psar(h, l, step=0.02, max_step=0.2):
    hv = h.values; lv = l.values; n = len(hv)
    if n == 0: return pd.Series([], index=h.index)
    ps = np.zeros(n); bull = True; af = step; ep = hv[0]; ps[0] = lv[0]
    for i in range(1, n):
        p0 = ps[i-1]
        if bull:
            ps[i] = min(p0 + af*(ep - p0), lv[i-1] if i>0 else lv[i])
            if lv[i] < ps[i]:
                bull = False; ps[i] = ep; ep = lv[i]; af = step
            else:
                if hv[i] > ep: ep = hv[i]; af = min(af+step, max_step)
        else:
            ps[i] = max(p0 + af*(ep - p0), hv[i-1] if i>0 else hv[i])
            if hv[i] > ps[i]:
                bull = True; ps[i] = ep; ep = hv[i]; af = step
            else:
                if lv[i] < ep: ep = lv[i]; af = min(af+step, max_step)
    return pd.Series(ps, index=h.index)

def stoch_rsi(c, n=14, k=3, d=3):
    r = rsi_wilder(c, n)
    rmin = r.rolling(n, min_periods=n).min()
    rmax = r.rolling(n, min_periods=n).max()
    st = 100 * (r - rmin) / (rmax - rmin).replace(0, np.nan)
    kline = st.rolling(k, min_periods=k).mean()
    dline = kline.rolling(d, min_periods=d).mean()
    return kline.clip(0,100), dline.clip(0,100)

def compute_indicators(df: pd.DataFrame) -> dict:
    out = {}
    c = df["Close"].astype(float)
    h = df["High"].astype(float)
    l = df["Low"].astype(float)
    v = df.get("Volume", pd.Series(index=df.index, dtype=float)).fillna(0).astype(float)

    out["EMA9"]   = ema(c, 9)
    out["EMA21"]  = ema(c, 21)
    out["EMA50"]  = ema(c, 50)
    out["EMA100"] = ema(c, 100)
    out["EMA200"] = ema(c, 200)

    sma20 = c.rolling(20, min_periods=20).mean()
    std20 = c.rolling(20, min_periods=20).std()
    out["BB_basis"] = sma20
    out["BB_upper"] = sma20 + 2*std20
    out["BB_lower"] = sma20 - 2*std20

    out["ATR20"]    = atr(h, l, c, 20)
    out["KC_basis"] = ema(c, 20)
    out["KC_upper"] = out["KC_basis"] + 2*out["ATR20"]
    out["KC_lower"] = out["KC_basis"] - 2*out["ATR20"]

    out["RSI"] = rsi_wilder(c, 14)
    m, s, hist = macd_tv(c, 12, 26, 9)
    out["MACD"] = m; out["MACD_sig"] = s; out["MACD_hist"] = hist
    kf, df_ = stochastic_full(h, l, c, 14, 3, 3)
    out["%K"] = kf; out["%D"] = df_
    sk, sd = stoch_rsi(c, 14, 3, 3)
    out["ST_RSI_K"] = sk; out["ST_RSI_D"] = sd

    out["PSAR"] = psar(h, l)
    return out
