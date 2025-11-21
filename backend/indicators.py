import numpy as np
import pandas as pd
def _ema(s: pd.Series, n: int):
    return s.ewm(span=n, adjust=False).mean()
def _rsi(close: pd.Series, n: int = 14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1 / n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi
def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, k: int = 14, d: int = 3, smooth: int = 3):
    ll = low.rolling(k).min()
    hh = high.rolling(k).max()
    raw_k = 100 * (close - ll) / (hh - ll)
    stoch_k = raw_k.rolling(smooth).mean()
    stoch_d = stoch_k.rolling(d).mean()
    return stoch_k, stoch_d
def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist
def _bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std(ddof=0)
    up = mid + k * sd
    dn = mid - k * sd
    return mid, up, dn
def compute(df: pd.DataFrame):
    c = pd.Series(df["close"])
    h = pd.Series(df["high"])
    l = pd.Series(df["low"])
    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3, 3)
    macdLine, macdSignal, macdHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendH = h.rolling(20).max()
    trendL = l.rolling(20).min()
    def _clean(s: pd.Series):
        s = s.replace([np.inf, -np.inf], np.nan)
        s = s.astype(float)
        s = s.where(pd.notna(s), None)
        return s.tolist()
    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi": _clean(rsi),
        "stochK": _clean(stochK),
        "stochD": _clean(stochD),
        "macdLine": _clean(macdLine),
        "macdSignal": _clean(macdSignal),
        "macdHist": _clean(macdHist),
        "bbMid": _clean(bbMid),
        "bbUp": _clean(bbUp),
        "bbDn": _clean(bbDn),
        "trendH": _clean(trendH),
        "trendL": _clean(trendL),
    }
