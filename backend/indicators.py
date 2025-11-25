import numpy as np
import pandas as pd

def ema(s, n):
    return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = -delta.clip(upper=0.0)
    gain = up.ewm(alpha=1/n, adjust=False).mean()
    loss = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(0)

def macd(close, fast=12, slow=26, signal=9):
    fast_ema = ema(close, fast)
    slow_ema = ema(close, slow)
    m = fast_ema - slow_ema
    s = ema(m, signal)
    h = m - s
    return m, s, h

def atr(h, l, c, n=14):
    prev_c = c.shift(1)
    tr = pd.concat([
        (h - l),
        (h - prev_c).abs(),
        (l - prev_c).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/n, adjust=False).mean()

def stoch_rsi(close, rsi_len=14, k_len=3, d_len=3):
    r = rsi_wilder(close, rsi_len)
    low = r.rolling(rsi_len, min_periods=1).min()
    high = r.rolling(rsi_len, min_periods=1).max()
    stoch = (r - low) / (high - low).replace(0, np.nan) * 100
    k = stoch.rolling(k_len, min_periods=1).mean()
    d = k.rolling(d_len, min_periods=1).mean()
    return k.fillna(0), d.fillna(0)

def keltner_channel(h, l, c, ema_len=20, atr_len=10, mult=2.0):
    basis = ema(c, ema_len)
    a = atr(h, l, c, atr_len)
    upper = basis + mult * a
    lower = basis - mult * a
    return basis, upper, lower

def psar(high, low, step=0.02, max_step=0.2):
    af = step
    ep = high.iloc[0]
    psar = [low.iloc[0]]
    bull = True
    for i in range(1, len(high)):
        prev_psar = psar[-1]
        if bull:
            ps = prev_psar + af * (ep - prev_psar)
            ps = min(ps, low.iloc[i-1], low.iloc[i-2] if i > 1 else low.iloc[i-1])
            if high.iloc[i] > ep:
                ep = high.iloc[i]
                af = min(af + step, max_step)
            if low.iloc[i] < ps:
                bull = False
                ps = ep
                ep = low.iloc[i]
                af = step
        else:
            ps = prev_psar + af * (ep - prev_psar)
            ps = max(ps, high.iloc[i-1], high.iloc[i-2] if i > 1 else high.iloc[i-1])
            if low.iloc[i] < ep:
                ep = low.iloc[i]
                af = min(af + step, max_step)
            if high.iloc[i] > ps:
                bull = True
                ps = ep
                ep = high.iloc[i]
                af = step
        psar.append(ps)
    return pd.Series(psar, index=high.index)

def compute_indicators(df):
    df = df.copy()
    c, h, l = df["Close"], df["High"], df["Low"]
    df["RSI"] = rsi_wilder(c, 14)
    m, s, hist = macd(c, 12, 26, 9)
    df["MACD"] = m
    df["MACD_signal"] = s
    df["MACD_hist"] = hist
    k, d = stoch_rsi(c, 14, 3, 3)
    df["ST_RSI_K"] = k
    df["ST_RSI_D"] = d
    df["ATR14"] = atr(h, l, c, 14)
    kc_b, kc_u, kc_lo = keltner_channel(h, l, c, 20, 10, 2.0)
    df["KC_basis"] = kc_b
    df["KC_upper"] = kc_u
    df["KC_lower"] = kc_lo
    df["PSAR"] = psar(h, l)
    cols = ["Open","High","Low","Close","RSI","MACD","MACD_signal","MACD_hist","ST_RSI_K","ST_RSI_D","ATR14","KC_basis","KC_upper","KC_lower","PSAR"]
    return df[cols]
