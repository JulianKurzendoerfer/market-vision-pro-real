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
    r = requests.get(f"{EODHD_BASE}/{path}", params=params, timeout=25)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"EODHD error {r.status_code}: {r.text[:300]}")
    try:
        return r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="EODHD returned non-JSON response")

def _ema(values, span):
    if not values:
        return []
    alpha = 2 / (span + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out

def _rsi(values, period=14):
    if len(values) < period + 1:
        return [None] * len(values)
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    rsi = [None] * (period)
    if avg_loss == 0:
        rsi.append(100.0)
    else:
        rs = avg_gain / avg_loss
        rsi.append(100 - (100 / (1 + rs)))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))

    return [None] + rsi

def _macd(values, fast=12, slow=26, signal=9):
    ema_fast = _ema(values, fast)
    ema_slow = _ema(values, slow)
    macd_line = [a - b for a, b in zip(ema_fast, ema_slow)]
    signal_line = _ema(macd_line, signal)
    hist = [m - s for m, s in zip(macd_line, signal_line)]
    return macd_line, signal_line, hist

def _sma(values, period):
    out = []
    s = 0.0
    for i, v in enumerate(values):
        s += v
        if i >= period:
            s -= values[i - period]
        if i + 1 < period:
            out.append(None)
        else:
            out.append(s / period)
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
    upper = []
    lower = []
    for m, s in zip(mid, sd):
        if m is None or s is None:
            upper.append(None)
            lower.append(None)
        else:
            upper.append(m + std_mul * s)
            lower.append(m - std_mul * s)
    return upper, mid, lower

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

@app.get("/api/quote")
def quote(symbol: str = Query(..., min_length=1, max_length=32)):
    data = _get(f"real-time/{symbol}", {})
    if isinstance(data, dict) and data.get("code") and data.get("message"):
        raise HTTPException(status_code=502, detail=f"EODHD: {data.get('message')}")
    return data

@app.get("/api/candles")
def candles(
    symbol: str = Query(..., min_length=1, max_length=32),
    period: str = Query("d", pattern="^(d|w|m)$"),
    days: int = Query(200, ge=30, le=5000),
):
    to_d = date.today()
    from_d = to_d - timedelta(days=days)
    data = _get(
        f"eod/{symbol}",
        {"from": from_d.isoformat(), "to": to_d.isoformat(), "period": period},
    )
    if not isinstance(data, list) or len(data) == 0:
        raise HTTPException(status_code=502, detail="No candle data returned")
    return data

@app.get("/api/indicators")
def indicators(
    symbol: str = Query(..., min_length=1, max_length=32),
    period: str = Query("d", pattern="^(d|w|m)$"),
    days: int = Query(320, ge=60, le=5000),
):
    raw = candles(symbol=symbol, period=period, days=days)
    raw_sorted = sorted(raw, key=lambda x: x.get("date", ""))
    closes = []
    series = []
    for row in raw_sorted:
        c = row.get("close")
        d = row.get("date")
        if c is None or d is None:
            continue
        try:
            c = float(c)
        except Exception:
            continue
        closes.append(c)
        series.append({
            "date": d,
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": c,
            "volume": row.get("volume"),
        })
    if len(closes) < 60:
        raise HTTPException(status_code=502, detail="Not enough candle data")

    rsi14 = _rsi(closes, 14)
    macd, macd_sig, macd_hist = _macd(closes, 12, 26, 9)
    bb_u, bb_m, bb_l = _bb(closes, 20, 2.0)

    out = []
    for i in range(len(series)):
        row = dict(series[i])
        row["rsi14"] = rsi14[i]
        row["macd"] = macd[i]
        row["macd_signal"] = macd_sig[i]
        row["macd_hist"] = macd_hist[i]
        row["bb_upper"] = bb_u[i]
        row["bb_middle"] = bb_m[i]
        row["bb_lower"] = bb_l[i]
        out.append(row)

    last = out[-1]
    return {"symbol": symbol.upper(), "last": last, "series": out[-250:]}
