import os
from datetime import date, timedelta
import math
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

EODHD_BASE = "https://eodhd.com/api"

def _key() -> str:
    k = os.getenv("EODHD_API_KEY") or os.getenv("EODHD_TOKEN")
    if not k:
        raise HTTPException(status_code=500, detail="Missing EODHD_API_KEY env var")
    return k

def _get(path: str, params: dict):
    params = {**params, "api_token": _key(), "fmt": "json"}
    r = requests.get(f"{EODHD_BASE}/{path}", params=params, timeout=40)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"EODHD error {r.status_code}: {r.text[:300]}")
    try:
        return r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="EODHD returned non-JSON response")

def _get_fundamentals(symbol: str):
    return _get(f"fundamentals/{symbol}", {})

def _ipo_date(symbol: str):
    try:
        f = _get_fundamentals(symbol)
        d = None
        if isinstance(f, dict):
            g = f.get("General") if isinstance(f.get("General"), dict) else None
            if g:
                d = g.get("IPODate") or g.get("IPO_Date") or g.get("IPO")
        if isinstance(d, str) and len(d) >= 10:
            y,m,dd = d[:10].split("-")
            return date(int(y), int(m), int(dd))
    except Exception:
        pass
    return date(1970,1,1)

def _ema(values, span):
    if not values:
        return []
    alpha = 2 / (span + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out

def _sma(values, period):
    out = []
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i - period]
        out.append(None if i + 1 < period else s / period)
    return out

def _std(values, period):
    out = []
    for i in range(len(values)):
        if i + 1 < period:
            out.append(None)
            continue
        window = values[i - period + 1 : i + 1]
        m = sum(window) / period
        var = sum((x - m) ** 2 for x in window) / period
        out.append(math.sqrt(var))
    return out

def _bb(values, period=20, std_mul=2.0):
    mid = _sma(values, period)
    sd = _std(values, period)
    upper, lower = [], []
    for m, s in zip(mid, sd):
        if m is None or s is None:
            upper.append(None)
            lower.append(None)
        else:
            upper.append(m + std_mul * s)
            lower.append(m - std_mul * s)
    return upper, mid, lower

def _rsi(values, period=14):
    if len(values) < period + 1:
        return [None] * len(values)
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi = [None] * period
    rsi.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rsi.append(100.0 if avg_loss == 0 else 100 - (100 / (1 + (avg_gain / avg_loss))))
    return [None] + rsi

def _macd(values, fast=12, slow=26, signal=9):
    ema_fast = _ema(values, fast)
    ema_slow = _ema(values, slow)
    macd_line = [a - b for a, b in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal)
    hist = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, hist

def _stoch(highs, lows, closes, period=14, smooth_d=3):
    k = [None] * len(closes)
    for i in range(len(closes)):
        if i + 1 < period:
            continue
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        denom = (hh - ll)
        k[i] = 0.0 if denom == 0 else 100.0 * (closes[i] - ll) / denom
    d = [None] * len(closes)
    for i in range(len(closes)):
        window = [x for x in k[max(0, i - smooth_d + 1): i + 1] if x is not None]
        d[i] = (sum(window) / len(window)) if window else None
    return k, d

def _sr_levels(candles, pivot_left=6, pivot_right=6, tol_pct=0.003, max_levels=18):
    if not candles or len(candles) < (pivot_left + pivot_right + 10):
        return []
    pivots = []
    n = len(candles)
    for i in range(pivot_left, n - pivot_right):
        lo = candles[i]["low"]
        hi = candles[i]["high"]
        is_low = True
        is_high = True
        for j in range(i - pivot_left, i + pivot_right + 1):
            if candles[j]["low"] < lo:
                is_low = False
            if candles[j]["high"] > hi:
                is_high = False
            if not is_low and not is_high:
                break
        if is_low:
            pivots.append(("support", float(lo)))
        if is_high:
            pivots.append(("resistance", float(hi)))
    if not pivots:
        return []
    supports = [p[1] for p in pivots if p[0] == "support"]
    resistances = [p[1] for p in pivots if p[0] == "resistance"]
    def cluster(values):
        values = sorted(values)
        clusters = []
        for v in values:
            placed = False
            for c in clusters:
                mid = c["sum"] / c["count"]
                if abs(v - mid) / mid <= tol_pct:
                    c["sum"] += v
                    c["count"] += 1
                    placed = True
                    break
            if not placed:
                clusters.append({"sum": v, "count": 1})
        out = [{"value": c["sum"] / c["count"], "strength": c["count"]} for c in clusters]
        out.sort(key=lambda x: (-x["strength"], -x["value"]))
        return out
    sup = cluster(supports)
    res = cluster(resistances)
    all_lvls = []
    for x in sup:
        all_lvls.append({"type": "support", "value": round(float(x["value"]), 6), "strength": int(x["strength"])})
    for x in res:
        all_lvls.append({"type": "resistance", "value": round(float(x["value"]), 6), "strength": int(x["strength"])})
    all_lvls.sort(key=lambda x: (-x["strength"], x["type"]))
    return all_lvls[:max_levels]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/tv")
def tv(
    symbol: str = Query(..., min_length=1, max_length=32),
    period: str = Query("d", pattern="^(d|w|m)$"),
    full: int = Query(1, ge=0, le=1),
    days: int = Query(520, ge=120, le=80000),
):
    to_d = date.today()
    if int(full) == 1:
        start = _ipo_date(symbol)
        raw = _get(f"eod/{symbol}", {"from": start.isoformat(), "to": to_d.isoformat(), "period": period})
    else:
        from_d = to_d - timedelta(days=days)
        raw = _get(f"eod/{symbol}", {"from": from_d.isoformat(), "to": to_d.isoformat(), "period": period})
    if not isinstance(raw, list) or len(raw) == 0:
        raise HTTPException(status_code=502, detail="No candle data returned")
    raw_sorted = sorted(raw, key=lambda x: x.get("date", ""))
    candles = []
    closes, highs, lows = [], [], []
    for r in raw_sorted:
        d = r.get("date")
        o = r.get("open")
        h = r.get("high")
        l = r.get("low")
        c = r.get("close")
        if d is None or h is None or l is None or c is None:
            continue
        try:
            c = float(c)
            h = float(h)
            l = float(l)
            o = float(o) if o is not None else c
        except Exception:
            continue
        if c <= 0 or h <= 0 or l <= 0 or h < l:
            continue
        candles.append({"time": d, "open": o, "high": h, "low": l, "close": c})
        closes.append(c)
        highs.append(h)
        lows.append(l)
    if len(candles) < 120:
        raise HTTPException(status_code=502, detail="Not enough candle data")
    bb_u, bb_m, bb_l = _bb(closes, 20, 2.0)
    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)
    ema100 = _ema(closes, 100)
    ema200 = _ema(closes, 200)
    rsi14 = _rsi(closes, 14)
    stoch_k, stoch_d = _stoch(highs, lows, closes, 14, 3, 3)
    macd, macd_sig, macd_hist = _macd(closes, 12, 26, 9)
    overlays = []
    for i in range(len(candles)):
        overlays.append({
            "time": candles[i]["time"],
            "close": closes[i],
            "bb_upper": bb_u[i],
            "bb_middle": bb_m[i],
            "bb_lower": bb_l[i],
            "ema20": ema20[i] if i < len(ema20) else None,
            "ema50": ema50[i] if i < len(ema50) else None,
            "ema100": ema100[i] if i < len(ema100) else None,
            "ema200": ema200[i] if i < len(ema200) else None,
            "rsi14": rsi14[i] if i < len(rsi14) else None,
            "stoch_k": stoch_k[i],
            "stoch_d": stoch_d[i],
            "macd": macd[i] if i < len(macd) else None,
            "macd_signal": macd_sig[i] if i < len(macd_sig) else None,
            "macd_hist": macd_hist[i] if i < len(macd_hist) else None,
        })
    last = overlays[-1]
    levels = _sr_levels(candles)
    return {"symbol": symbol.upper(), "candles": candles, "overlays": overlays, "last": last, "levels": levels}
