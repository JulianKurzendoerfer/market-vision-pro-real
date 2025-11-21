import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int):
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close: pd.Series, n: int = 14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1/n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1/n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, k: int = 14, smooth:int = 3, d:int = 3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    stoch_k = raw_k.rolling(smooth).mean()
    stoch_d = stoch_k.rolling(d).mean()
    return stoch_k, stoch_d

def _macd(close: pd.Series, fast:int=12, slow:int=26, signal:int=9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist

def _bollinger(close: pd.Series, n:int=20, k:float=2.0):
    ma = close.rolling(n).mean()
    sd = close.rolling(n).std(ddof=0)
    bb_up = ma + k*sd
    bb_dn = ma - k*sd
    return ma, bb_up, bb_dn

def _clean_series(s: pd.Series):
    s = pd.to_numeric(s, errors="coerce").replace([np.inf, -np.inf], np.nan)
    return s.astype(float).where(pd.notna(s), None).tolist()

def compute_bundle(df: pd.DataFrame):
    c = pd.to_numeric(df["close"], errors="coerce")
    h = pd.to_numeric(df["high"], errors="coerce")
    l = pd.to_numeric(df["low"], errors="coerce")

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)

    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3, 3)

    macdLine, macdSignal, macdHist = _macd(c, 12, 26, 9)

    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)

    trendH = h.rolling(20).max()
    trendL = l.rolling(20).min()

    return {
        "ema20": _clean_series(ema20),
        "ema50": _clean_series(ema50),
        "rsi": _clean_series(rsi14),
        "stockK": _clean_series(stochK),
        "stockD": _clean_series(stochD),
        "macdLine": _clean_series(macdLine),
        "macdSignal": _clean_series(macdSignal),
        "macdHist": _clean_series(macdHist),
        "bbMid": _clean_series(bbMid),
        "bbUp": _clean_series(bbUp),
        "bbDn": _clean_series(bbDn),
        "trendH": _clean_series(trendH),
        "trendL": _clean_series(trendL),
    }
