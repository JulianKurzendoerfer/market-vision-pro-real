import numpy as np
import pandas as pd

def ema(s, n):
    return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = -d.clip(upper=0.0)
    avg_gain = up.ewm(alpha=1/n, adjust=False).mean()
    avg_loss = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = avg_gain / (avg_loss.replace(0, np.nan))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)

def macd(close, fast=12, slow=26, signal=9):
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    m = ema_fast - ema_slow
    s = ema(m, signal)
    h = m - s
    return m, s, h

def bbands(close, n=20, k=2):
    ma = close.rolling(int(n)).mean()
    sd = close.rolling(int(n)).std(ddof=0)
    upper = ma + k * sd
    lower = ma - k * sd
    return ma, upper, lower

def atr(h, l, c, n=14):
    prev_c = c.shift(1)
    tr = pd.concat([(h - l).abs(), (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(int(n)).mean()

def keltner_channels(h, l, c, n=20, atr_n=14, mult=2):
    basis = c.rolling(int(n)).mean()
    rng = atr(h, l, c, atr_n)
    upper = basis + mult * rng
    lower = basis - mult * rng
    return basis, upper, lower

def stoch_rsi(close, n=14, k=3, d=3):
    r = rsi_wilder(close, n)
    low = r.rolling(int(n)).min()
    high = r.rolling(int(n)).max()
    stoch = (r - low) / (high - low).replace(0, np.nan)
    kf = stoch.rolling(int(k)).mean()
    df = kf.rolling(int(d)).mean()
    return (kf * 100), (df * 100)

def compute_indicators(df):
    out = {}
    c = df["Close"]; h = df["High"]; l = df["Low"]
    out["EMA20"] = ema(c, 20)
    out["EMA50"] = ema(c, 50)
    out["EMA200"] = ema(c, 200)
    out["RSI"] = rsi_wilder(c, 14)
    m, s, hst = macd(c, 12, 26, 9)
    out["MACD"] = m; out["MACD_signal"] = s; out["MACD_hist"] = hst
    b, u, d = bbands(c, 20, 2); out["BB_basis"] = b; out["BB_upper"] = u; out["BB_lower"] = d
    out["ATR20"] = atr(h, l, c, 20)
    kb, ku, kl = keltner_channels(h, l, c, 20, 14, 2); out["KC_basis"] = kb; out["KC_upper"] = ku; out["KC_lower"] = kl
    kf, df_ = stoch_rsi(c, 14, 3, 3); out["ST_RSI_K"] = kf; out["ST_RSI_D"] = df_
    return out
