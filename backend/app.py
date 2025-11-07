import os, json
from datetime import datetime, timezone, timedelta
import requests, pandas as pd, numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS","*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
TOKEN = os.environ.get("EODHD_API_KEY","")

def _sym(s):
    s = (s or "").strip().upper()
    return s if "." in s else f"{s}.US"

def _get(url, params=None):
    p = dict(params or {})
    if "api_token" not in p: p["api_token"] = TOKEN
    p["fmt"] = "json"
    r = requests.get(url, params=p, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"upstream {r.status_code}")
    try:
        return r.json()
    except Exception:
        raise HTTPException(status_code=502, detail="bad upstream json")

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/resolve")
def resolve(q: str, prefer: str = "US", limit: int = 10):
    data = _get(f"https://eodhd.com/api/search/{q}", {"limit": limit})
    out = []
    for i in data:
        code = i.get("Code") or i.get("code") or ""
        exch = i.get("Exchange") or i.get("exchange") or ""
        name = i.get("Name") or i.get("name") or ""
        score = 2 if prefer and exch.upper() == prefer.upper() else 1
        out.append({"code": code, "exchange": exch, "name": name, "score": score})
    out.sort(key=lambda x: (-x["score"], x["code"]))
    return out

@app.get("/v1/ohlcv")
def ohlcv(symbol: str, bars: int = 120):
    s = _sym(symbol)
    end = datetime.utcnow().date()
    start = end - timedelta(days=bars*2)
    rows = _get(f"https://eodhd.com/api/eod/{s}", {"from": start.isoformat(), "to": end.isoformat(), "order":"d"})
    if not rows:
        raise HTTPException(status_code=404, detail="no data")
    rows = rows[-bars:]
    last = rows[-1]["close"]
    prev = rows[-2]["close"] if len(rows) > 1 else None
    return {"symbol": symbol.upper(), "last": float(last), "previousClose": float(prev) if prev is not None else None, "bars": rows}

@app.get("/v1/indicators")
def indicators(symbol: str, bars: int = 200):
    s = _sym(symbol)
    end = datetime.utcnow().date()
    start = end - timedelta(days=bars*2)
    rows = _get(f"https://eodhd.com/api/eod/{s}", {"from": start.isoformat(), "to": end.isoformat(), "order":"d"})
    if not rows or len(rows) < 50:
        raise HTTPException(status_code=404, detail="no data")
    df = pd.DataFrame(rows)
    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]

    delta = close.diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    rs = pd.Series(up).rolling(14).mean() / pd.Series(down).rolling(14).mean()
    rsi = 100 - (100 / (1 + rs))
    rsi_val = float(rsi.iloc[-1])

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()

    n = 14
    lowest = low.rolling(n).min()
    highest = high.rolling(n).max()
    stoch_k = ((close - lowest) / (highest - lowest) * 100).rolling(3).mean()
    stoch_d = stoch_k.rolling(3).mean()

    return {
        "symbol": symbol.upper(),
        "rsi": round(rsi_val, 2),
        "ema20": round(float(ema20), 2),
        "ema50": round(float(ema50), 2),
        "macdLine": round(float(macd_line.iloc[-1]), 2),
        "macdSignal": round(float(macd_signal.iloc[-1]), 2),
        "stochK": round(float(stoch_k.iloc[-1]), 2) if not stoch_k.empty else None,
        "stochD": round(float(stoch_d.iloc[-1]), 2) if not stoch_d.empty else None
    }
