import os
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .indicators import compute_bundle

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_headers=["*"],
    allow_methods=["*"],
)

RANGE_MAP = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "5Y": 365*5,
    "MAX": 365*30,
}

def _date_from_range(r: str) -> datetime:
    days = RANGE_MAP.get(r.upper(), 365)
    return datetime.utcnow() - timedelta(days=days)

def fetch_ohlc(symbol: str, r: str) -> pd.DataFrame:
    start = _date_from_range(r)
    df = yf.download(symbol, start=start.date().isoformat(), progress=False, auto_adjust=False)
    if df is None or df.empty:
        return pd.DataFrame(columns=["open","high","low","close","volume"])
    out = df.rename(columns=str.lower)[["open","high","low","close","volume"]].copy()
    out.reset_index(inplace=True)
    out["t"] = pd.to_datetime(out["date"]).astype("int64")//10**9
    return out[["t","open","high","low","close","volume"]]

def to_list(x: pd.Series):
    y = pd.to_numeric(x, errors="coerce").replace([np.inf,-np.inf], np.nan)
    return y.astype(float).where(pd.notna(y), None).tolist()

class ComputeBody(BaseModel):
    close: List[float]
    high: List[float]
    low: List[float]

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "ts": int(time.time())}

@app.post("/v1/compute")
def v1_compute(body: ComputeBody):
    n = len(body.close)
    if not (len(body.high)==n and len(body.low)==n and n>0):
        return {"ok": False, "error": "invalid input"}
    df = pd.DataFrame({"close": body.close, "high": body.high, "low": body.low})
    inds = compute_bundle(df)
    return {"ok": True, "indicators": inds}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query("1Y")):
    df = fetch_ohlc(symbol, range)
    if df.empty:
        return {"ok": False, "error": "no_data"}
    inds = compute_bundle(df.rename(columns={"t":"time"}))
    meta = {
        "symbol": symbol.upper(),
        "currency": None,
        "tz": "UTC",
    }
    out = {
        "ok": True,
        "asof": datetime.utcnow().isoformat(timespec="seconds")+"Z",
        "meta": meta,
        "t": to_list(df["t"]),
        "o": to_list(df["open"]),
        "h": to_list(df["high"]),
        "l": to_list(df["low"]),
        "c": to_list(df["close"]),
        "v": to_list(df["volume"]),
        "indicators": inds,
    }
    return out
