import numpy as np
import pandas as pd

def ema(s, n): return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    au = up.ewm(alpha=1/n, adjust=False).mean()
    ad = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.clip(0, 100)

def macd(close, fast=12, slow=26, signal=9):
    m = ema(close, fast) - ema(close, slow)
    s = ema(m, signal)
    h = m - s
    return m, s, h

def atr(h, l, c, n=20, ema_mode=True):
    pc = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean() if ema_mode else tr.rolling(n).mean()

def stochastic_full(h, l, c, k=14, ks=3, d=3):
    hh = h.rolling(k, min_periods=k).max()
    ll = l.rolling(k, min_periods=k).min()
    r = 100 * (c - ll) / (hh - ll).replace(0, np.nan)
    K = r.rolling(ks, min_periods=ks).mean()
    D = K.rolling(d, min_periods=d).mean()
    return K.clip(0, 100), D.clip(0, 100)

def psar(h, l, step=0.02, max_step=0.2):
    hv, lv = h.values, l.values
    n = len(hv)
    if n == 0: return pd.Series([], index=h.index)
    out = np.zeros(n, float)
    bull = True
    af = step
    ep = hv[0]
    out[0] = lv[0]
    for i in range(1, n):
        prev = out[i-1]
        if bull:
            out[i] = prev + af*(ep - prev)
            out[i] = min(out[i], lv[i-1] if i-1>=0 else out[i], lv[i-2] if i-2>=0 else out[i])
            if lv[i] < out[i]:
                bull = False
                out[i] = ep
                ep = lv[i]
                af = step
            else:
                if hv[i] > ep:
                    ep = hv[i]
                    af = min(af+step, max_step)
        else:
            out[i] = prev + af*(ep - prev)
            out[i] = max(out[i], hv[i-1] if i-1>=0 else out[i], hv[i-2] if i-2>=0 else out[i])
            if hv[i] > out[i]:
                bull = True
                out[i] = ep
                ep = hv[i]
                af = step
            else:
                if lv[i] < ep:
                    ep = lv[i]
                    af = min(af+step, max_step)
    return pd.Series(out, index=h.index)

def _extrema_idx(x, window=10):
    a = x.astype(float).values
    n = len(a)
    lows, highs = [], []
    for i in range(window, n-window):
        w = a[i-window:i+window+1]
        if np.isfinite(w).all():
            if a[i] <= w.min(): lows.append(i)
            if a[i] >= w.max(): highs.append(i)
    return np.array(lows, int), np.array(highs, int)

def _cluster_levels(vals, tol=0.01, relative=True):
    if len(vals)==0: return np.array([]), np.array([]), np.array([])
    v = np.sort(np.array(vals, float))
    centers, counts = [], []
    cur = [v[0]]
    for z in v[1:]:
        ok = (abs(z-cur[-1]) <= tol*max(1.0, abs(cur[-1]))) if relative else (abs(z-cur[-1])<=tol)
        if ok: cur.append(z)
        else:
            centers.append(np.mean(cur)); counts.append(len(cur)); cur=[z]
    centers.append(np.mean(cur)); counts.append(len(cur))
    centers = np.array(centers, float)
    counts = np.array(counts, float)
    strength = (counts - counts.min()) / (counts.max() - counts.min() + 1e-9)
    return centers, counts, strength

def trend_panel(close, window=10, tol=0.01, relative=True):
    lows, highs = _extrema_idx(close, window)
    levels, counts, strength = _cluster_levels(list(close.iloc[lows])+list(close.iloc[highs]), tol, relative)
    return dict(lows=lows, highs=highs, levels=levels, counts=counts, strength=strength)

def compute_indicators(df):
    out = df.copy()
    out["EMA9"] = ema(out["Close"], 9)
    out["EMA21"] = ema(out["Close"], 21)
    out["EMA50"] = ema(out["Close"], 50)
    out["EMA100"] = ema(out["Close"], 100)
    out["EMA200"] = ema(out["Close"], 200)
    sma20 = out["Close"].rolling(20, min_periods=20).mean()
    std20 = out["Close"].rolling(20, min_periods=20).std()
    out["BB_mid"] = sma20
    out["BB_upper"] = sma20 + 2*std20
    out["BB_lower"] = sma20 - 2*std20
    out["ATR20"] = atr(out["High"], out["Low"], out["Close"], 20, True)
    out["KC_mid"] = ema(out["Close"], 20)
    out["KC_upper"] = out["KC_mid"] + 2*out["ATR20"]
    out["KC_lower"] = out["KC_mid"] - 2*out["ATR20"]
    out["RSI14"] = rsi_wilder(out["Close"], 14)
    m,s,h = macd(out["Close"], 12,26,9)
    out["MACD"], out["MACDS"], out["MACDH"] = m,s,h
    K,D = stochastic_full(out["High"], out["Low"], out["Close"], 14,3,3)
    out["STOCHK"], out["STOCHD"] = K,D
    out["PSAR"] = psar(out["High"], out["Low"])
    tp = trend_panel(out["Close"], 10, 0.01, True)
    return out, tp
