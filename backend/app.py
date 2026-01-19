import os
from datetime import date, timedelta
import math
import requests
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse, HTTPException, Query
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
    n = len(values)

    macd = [None] * n
    for i in range(n):
        if ema_fast[i] is None or ema_slow[i] is None:
            continue
        macd[i] = ema_fast[i] - ema_slow[i]

    signal_line = [None] * n
    first = None
    for i in range(n):
        if macd[i] is not None:
            first = i
            break

    if first is not None:
        start = first + signal - 1
        if start < n:
            ok = True
            s0 = 0.0
            for i in range(first, start + 1):
                if macd[i] is None:
                    ok = False
                    break
                s0 += macd[i]
            if ok:
                ema = s0 / signal
                signal_line[start] = ema
                alpha = 2.0 / (signal + 1.0)
                for i in range(start + 1, n):
                    if macd[i] is None:
                        continue
                    ema = alpha * macd[i] + (1.0 - alpha) * ema
                    signal_line[i] = ema

    hist = [None] * n
    for i in range(n):
        if macd[i] is None or signal_line[i] is None:
            continue
        hist[i] = macd[i] - signal_line[i]

    return hist

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

def _zigzag_pivots(candles, deviation=0.06, min_bars=8):
    if not candles or len(candles) < (min_bars + 5):
        return []
    pivots = []
    last_idx = 0
    last_price = candles[0]["close"]
    trend = 0
    extreme_idx = 0
    extreme_price = last_price

    def pct(a, b):
        if b == 0:
            return 0.0
        return (a - b) / b

    for i in range(1, len(candles)):
        hi = candles[i]["high"]
        lo = candles[i]["low"]

        if trend == 0:
            up = pct(hi, last_price)
            dn = pct(last_price, lo)
            if up >= deviation:
                trend = 1
                extreme_idx = i
                extreme_price = hi
            elif dn >= deviation:
                trend = -1
                extreme_idx = i
                extreme_price = lo
            continue

        if trend == 1:
            if hi > extreme_price:
                extreme_price = hi
                extreme_idx = i
            rev = pct(extreme_price, lo)
            if rev >= deviation and (i - extreme_idx) >= min_bars:
                pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "H"})
                trend = -1
                last_idx = extreme_idx
                last_price = extreme_price
                extreme_idx = i
                extreme_price = lo

        else:
            if lo < extreme_price:
                extreme_price = lo
                extreme_idx = i
            rev = pct(hi, extreme_price)
            if rev >= deviation and (i - extreme_idx) >= min_bars:
                pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "L"})
                trend = 1
                last_idx = extreme_idx
                last_price = extreme_price
                extreme_idx = i
                extreme_price = hi

    if trend == 1:
        pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "H"})
    elif trend == -1:
        pivots.append({"idx": extreme_idx, "time": candles[extreme_idx]["time"], "price": float(extreme_price), "type": "L"})

    pivots = sorted(pivots, key=lambda x: x["idx"])
    cleaned = []
    for pv in pivots:
        if not cleaned:
            cleaned.append(pv)
            continue
        if pv["type"] == cleaned[-1]["type"]:
            if pv["type"] == "H":
                if pv["price"] >= cleaned[-1]["price"]:
                    cleaned[-1] = pv
            else:
                if pv["price"] <= cleaned[-1]["price"]:
                    cleaned[-1] = pv
        else:
            cleaned.append(pv)
    return cleaned

def _elliott_labels(pivots):
    if len(pivots) < 6:
        return []
    pv = pivots[-9:] if len(pivots) > 9 else pivots[:]
    labels = []
    def sign(a, b):
        return 1 if b > a else (-1 if b < a else 0)

    d = []
    for i in range(1, len(pv)):
        d.append(sign(pv[i-1]["price"], pv[i]["price"]))

    best = None
    for end in range(len(pv)-1, 4, -1):
        seq = pv[end-4:end+1]
        ds = [sign(seq[i]["price"], seq[i+1]["price"]) for i in range(4)]
        if ds[0] == 0:
            continue
        ok = True
        for j in range(1, 4):
            if ds[j] != -ds[j-1] or ds[j] == 0:
                ok = False
                break
        if not ok:
            continue
        best = seq
        break

    if best is None:
        best = pv[-5:]

    for i, name in enumerate(["1","2","3","4","5"]):
        labels.append({"time": best[i]["time"], "price": best[i]["price"], "text": name})

    tail = pivots[pivots.index(best[-1])+1:] if best[-1] in pivots else []
    if len(tail) >= 3:
        abc = tail[:3]
        for i, name in enumerate(["A","B","C"]):
            labels.append({"time": abc[i]["time"], "price": abc[i]["price"], "text": name})
    return labels

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
    pivots = _zigzag_pivots(candles)
    elliott = {"pivots": pivots, "labels": _elliott_labels(pivots)}
    return {"symbol": symbol.upper(), "candles": candles, "overlays": overlays, "last": last, "levels": levels, "elliott": elliott}
