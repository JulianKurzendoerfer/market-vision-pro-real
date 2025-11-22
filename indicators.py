import numpy as np
import pandas as pd

def ema(series, span):
    return series.ewm(span=int(span), adjust=False).mean()

def rsi_wilder(close, period=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    avg_up = up.ewm(alpha=1/period, adjust=False).mean()
    avg_dn = dn.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_up / avg_dn.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.clip(0, 100)

def atr(high, low, close, period=20, ema_mode=True):
    pc = close.shift(1)
    tr = pd.concat([(high-low).abs(), (high-pc).abs(), (low-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean() if ema_mode else tr.rolling(period).mean()

def macd_tv(close, fast=12, slow=26, signal=9):
    line = ema(close, fast) - ema(close, slow)
    sig  = ema(line, signal)
    hist = line - sig
    return line, sig, hist

def stochastic_full(high, low, close, k_period=14, k_smooth=3, d_period=3):
    hh = high.rolling(k_period, min_periods=k_period).max()
    ll = low.rolling(k_period, min_periods=k_period).min()
    denom = (hh-ll).replace(0, np.nan)
    raw_k = 100 * (close-ll) / denom
    k_slow = raw_k.rolling(k_smooth, min_periods=k_smooth).mean()
    d_slow = k_slow.rolling(d_period, min_periods=d_period).mean()
    return k_slow.clip(0,100), d_slow.clip(0,100)

def psar(high, low, step=0.02, max_step=0.2):
    h = high.values; l = low.values; n = len(h)
    if n == 0: return pd.Series([], index=high.index)
    ps = np.zeros(n, float); bull = True; af = step; ep = h[0]; ps[0] = l[0]
    for i in range(1, n):
        prev = ps[i-1]
        if bull:
            ps[i] = prev + af*(ep - prev)
            ps[i] = min(ps[i], l[i-1]) if i == 1 else min(ps[i], l[i-1], l[i-2])
            if l[i] < ps[i]:
                bull = False; ps[i] = ep; ep = l[i]; af = step
            else:
                if h[i] > ep: ep = h[i]; af = min(af+step, max_step)
        else:
            ps[i] = prev + af*(ep - prev)
            ps[i] = max(ps[i], h[i-1]) if i == 1 else max(ps[i], h[i-1], h[i-2])
            if h[i] > ps[i]:
                bull = True; ps[i] = ep; ep = h[i]; af = step
            else:
                if l[i] < ep: ep = l[i]; af = min(af+step, max_step)
    return pd.Series(ps, index=high.index)

def stoch_rsi(close, period=14, k=3, d=3):
    r = rsi_wilder(close, period)
    r_min = r.rolling(period, min_periods=period).min()
    r_max = r.rolling(period, min_periods=period).max()
    denom = (r_max - r_min).replace(0, np.nan)
    st = 100 * (r - r_min) / denom
    k_line = st.rolling(k, min_periods=k).mean()
    d_line = k_line.rolling(d, min_periods=d).mean()
    return k_line.clip(0,100), d_line.clip(0,100)

def compute_indicators(df):
    out = df.copy()
    out["EMA9"] = ema(out["Close"], 9)
    out["EMA21"] = ema(out["Close"], 21)
    out["EMA50"] = ema(out["Close"], 50)
    out["EMA100"] = ema(out["Close"], 100)
    out["EMA200"] = ema(out["Close"], 200)
    sma20 = out["Close"].rolling(20, min_periods=20).mean()
    std20 = out["Close"].rolling(20, min_periods=20).std()
    out["BB_basis"] = sma20
    out["BB_upper"] = sma20 + 2*std20
    out["BB_lower"] = sma20 - 2*std20
    out["ATR20"] = atr(out["High"], out["Low"], out["Close"], 20, ema_mode=True)
    out["KC_basis"] = ema(out["Close"], 20)
    out["KC_upper"] = out["KC_basis"] + 2*out["ATR20"]
    out["KC_lower"] = out["KC_basis"] - 2*out["ATR20"]
    out["RSI"] = rsi_wilder(out["Close"], 14)
    m_line, m_sig, m_hist = macd_tv(out["Close"], 12, 26, 9)
    out["MACD"] = m_line; out["MACD_sig"] = m_sig; out["MACD_hist"] = m_hist
    kf, df_ = stochastic_full(out["High"], out["Low"], out["Close"], 14, 3, 3)
    out["%K"] = kf; out["%D"] = df_
    sk, sd = stoch_rsi(out["Close"], 14, 3, 3)
    out["ST_RSI_K"] = sk; out["ST_RSI_D"] = sd
    out["PSAR"] = psar(out["High"], out["Low"])
    return out
