import numpy as np
import pandas as pd

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    roll_up = up.ewm(alpha=1 / n, adjust=False).mean()
    roll_dn = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = roll_up / roll_dn.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _stoch_kd(close: pd.Series, high: pd.Series, low: pd.Series, k: int = 14, d: int = 3) -> tuple[pd.Series, pd.Series]:
    hh = high.rolling(k).max()
    ll = low.rolling(k).min()
    rawk = 100 * (close - ll) / (hh - ll)
    stoch_k = rawk.rolling(d).mean()
    stoch_d = stoch_k.rolling(d).mean()
    return stoch_k, stoch_d

def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    line = ema_fast - ema_slow
    sig = _ema(line, signal)
    hist = line - sig
    return line, sig, hist

def _bollinger(close: pd.Series, n: int = 20, mult: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = close.rolling(n).mean()
    std = close.rolling(n).std()
    up = mid + mult * std
    dn = mid - mult * std
    return mid, up, dn

def _trend_hl(close: pd.Series, high: pd.Series, low: pd.Series, n: int = 20) -> pd.Series:
    up = close > high.rolling(n).max()
    dn = close < low.rolling(n).min()
    out = pd.Series(np.zeros(len(close), dtype=float), index=close.index)
    out[up.fillna(False)] = 1.0
    out[dn.fillna(False)] = -1.0
    return out

def compute_indicators(df: pd.DataFrame) -> dict:
    c = df["c"].astype(float)
    h = df["h"].astype(float)
    l = df["l"].astype(float)
    v = df["v"].astype(float)

    ema20 = _ema(c, 20)
    ema50 = _ema(c, 50)
    rsi14 = _rsi(c, 14)
    stochK, stochD = _stoch_kd(c, h, l, 14, 3)
    macLine, macSignal, macHist = _macd(c, 12, 26, 9)
    bbMid, bbUp, bbDn = _bollinger(c, 20, 2.0)
    trendHL = _trend_hl(c, h, l, 20)

    def _clean(s: pd.Series):
        return s.astype("float64").replace([pd.NA, np.inf, -np.inf], np.nan).tolist()

    return {
        "ema20": _clean(ema20),
        "ema50": _clean(ema50),
        "rsi14": _clean(rsi14),
        "stochK": _clean(stochK),
        "stochD": _clean(stochD),
        "macLine": _clean(macLine),
        "macSignal": _clean(macSignal),
        "macHist": _clean(macHist),
        "bbMid": _clean(bbMid),
        "bbUp": _clean(bbUp),
        "bbDn": _clean(bbDn),
        "trendHL": _clean(trendHL),
    }
