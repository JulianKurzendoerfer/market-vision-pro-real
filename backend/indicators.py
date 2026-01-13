import numpy as np
import pandas as pd

def ema(s, n): return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = -d.clip(upper=0.0)
    rs = ema(up, n) / ema(dn, n).replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd(close, fast=12, slow=26, sig=9):
    ema_f = ema(close, fast)
    ema_s = ema(close, slow)
    m = ema_f - ema_s
    s = ema(m, sig)
    h = m - s
    return m, s, h

def atr(df, n=14):
    h, l, c = df['High'], df['Low'], df['Close']
    prev_c = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-prev_c).abs(), (l-prev_c).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def bbands(close, n=20, k=2.0):
    m = close.rolling(n).mean()
    sd = close.rolling(n).std(ddof=0)
    up = m + k*sd
    lo = m - k*sd
    return m, up, lo

def keltner(df, n_ma=20, n_atr=14, mult=2.0):
    m = df['Close'].rolling(n_ma).mean()
    a = atr(df, n_atr)
    up = m + mult*a
    lo = m - mult*a
    return m, up, lo

def compute_indicators(df):
    df = df.copy()
    df['RSI'] = rsi_wilder(df['Close'], 14)
    macd_l, macd_s, macd_h = macd(df['Close'], 12, 26, 9)
    df['MACD'] = macd_l
    df['MACD_signal'] = macd_s
    df['MACD_hist'] = macd_h
    m, up, lo = bbands(df['Close'], 20, 2.0)
    df['BB_mid'] = m
    df['BB_up'] = up
    df['BB_lo'] = lo
    km, ku, kl = keltner(df, 20, 14, 2.0)
    df['KC_mid'] = km
    df['KC_up'] = ku
    df['KC_lo'] = kl
    df['ATR14'] = atr(df, 14)
    return df[['RSI','MACD','MACD_signal','MACD_hist','BB_mid','BB_up','BB_lo','KC_mid','KC_up','KC_lo','ATR14']]
