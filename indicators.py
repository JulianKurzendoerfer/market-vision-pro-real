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
    rsi = 100 - (100/(1+rs))
    return rsi.clip(0, 100)

def macd_tv(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s)
    ms = ema(m, sig)
    h = m - ms
    return m, ms, h

def atr(h, l, c, n=20, ema_mode=True):
    pc = c.shift(1)
    tr = pd.concat([(h-l).abs(), (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean() if ema_mode else tr.rolling(n).mean()

def stochastic_full(h, l, c, k=14, ks=3, d=3):
    hh = h.rolling(k, min_periods=k).max()
    ll = l.rolling(k, min_periods=k).min()
    denom = (hh-ll).replace(0, np.nan)
    rk = 100*(c-ll)/denom
    kslow = rk.rolling(ks, min_periods=ks).mean()
    dslow = kslow.rolling(d, min_periods=d).mean()
    return kslow.clip(0, 100), dslow.clip(0, 100)

def psar(h, l, step=0.02, max_step=0.2):
    h = h.values; l = l.values; n = len(h)
    if n == 0: return pd.Series([], index=pd.RangeIndex(0,0))
    ps = np.zeros(n); bull=True; af=step; ep=h[0]; ps[0]=l[0]
    for i in range(1,n):
        prev = ps[i-1]
        if bull:
            ps[i] = min(prev + af*(ep-prev), l[i-1] if i>0 else l[i])
            if l[i] < ps[i]:
                bull=False; ps[i]=ep; ep=l[i]; af=step
            else:
                if h[i] > ep: ep=h[i]; af=min(af+step, max_step)
        else:
            ps[i] = max(prev + af*(ep-prev), h[i-1] if i>0 else h[i])
            if h[i] > ps[i]:
                bull=True; ps[i]=ep; ep=h[i]; af=step
            else:
                if l[i] < ep: ep=l[i]; af=min(af+step, max_step)
    return pd.Series(ps, index=pd.RangeIndex(n))

def stoch_rsi(close, period=14, k=3, d=3):
    r = rsi_wilder(close, period)
    rmin = r.rolling(period, min_periods=period).min()
    rmax = r.rolling(period, min_periods=period).max()
    denom = (rmax-rmin).replace(0, np.nan)
    s = 100*(r-rmin)/denom
    kline = s.rolling(k, min_periods=k).mean()
    dline = kline.rolling(d, min_periods=d).mean()
    return kline.clip(0,100), dline.clip(0,100)

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
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
    m, ms, hist = macd_tv(out["Close"], 12, 26, 9)
    out["MACD"] = m; out["MACD_sig"] = ms; out["MACD_hist"] = hist
    kf, df_ = stochastic_full(out["High"], out["Low"], out["Close"], 14, 3, 3)
    out["%K"] = kf; out["%D"] = df_
    sk, sd = stoch_rsi(out["Close"], 14, 3, 3)
    out["ST_RSI_K"] = sk; out["ST_RSI_D"] = sd
    out["PSAR"] = psar(out["High"], out["Low"])
    return out
