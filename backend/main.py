import os
from datetime import date, timedelta
import numpy as np
import pandas as pd
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

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()

def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    macd = _ema(close, fast) - _ema(close, slow)
    sig = _ema(macd, signal)
    hist = macd - sig
    return macd, sig, hist

def _bb(close: pd.Series, period: int = 20, std: float = 2.0):
    m = close.rolling(period).mean()
    s = close.rolling(period).std()
    upper = m + std * s
    lower = m - std * s
    return upper, m, lower

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
    days: int = Query(260, ge=60, le=5000),
):
    raw = candles(symbol=symbol, period=period, days=days)
    df = pd.DataFrame(raw)
    for c in ["open", "high", "low", "close", "adjusted_close", "volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    if "date" not in df.columns or "close" not in df.columns:
        raise HTTPException(status_code=502, detail="Unexpected candle schema")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").dropna(subset=["close"])
    close = df["close"]

    rsi = _rsi(close, 14)
    macd, sig, hist = _macd(close)
    up, mid, low = _bb(close)

    out = df.tail(250).copy()
    out["rsi14"] = rsi
    out["macd"] = macd
    out["macd_signal"] = sig
    out["macd_hist"] = hist
    out["bb_upper"] = up
    out["bb_middle"] = mid
    out["bb_lower"] = low

    cols = ["date","open","high","low","close","volume","rsi14","macd","macd_signal","macd_hist","bb_upper","bb_middle","bb_lower"]
    cols = [c for c in cols if c in out.columns]
    out = out[cols]
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    last = out.iloc[-1].to_dict()
    return {"symbol": symbol.upper(), "last": last, "series": out.to_dict(orient="records")}
