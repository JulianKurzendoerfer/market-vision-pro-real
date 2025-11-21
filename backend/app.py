import os
import sys
import pathlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

sys.path.append(str(pathlib.Path(__file__).resolve().parent))

import httpx
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel

from indicators import compute as compute_indicators, compute_bundle as indicators_bundle

app = FastAPI(title="MVP Backend", version="1.0.0")

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", None)

class OHLCIn(BaseModel):
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None
    meta: Optional[Dict[str, Any]] = None

def _to_df(obj: Dict[str, Any]) -> pd.DataFrame:
    t = obj.get("t", [])
    o = obj.get("o", [])
    h = obj.get("h", [])
    l = obj.get("l", [])
    c = obj.get("c", [])
    v = obj.get("v", [None]*len(c))
    df = pd.DataFrame({"t": t, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return df

async def fetch_ohlc(symbol: str, range_: str) -> pd.DataFrame:
    if not DATA_API_BASE:
        return pd.DataFrame()
    url = f"{DATA_API_BASE}/v1/bundle"
    headers = {}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    params = {"symbol": symbol, "range": range_}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url, params=params, headers=headers)
        r.raise_for_status()
        js = r.json()
    t = js.get("t", [])
    o = js.get("o", [])
    h = js.get("h", [])
    l = js.get("l", [])
    c = js.get("c", [])
    v = js.get("v", [None]*len(c))
    df = pd.DataFrame({"t": t, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return df

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query("1Y")):
    df = await fetch_ohlc(symbol, range)
    if df.empty:
        return {"ok": False, "error": "no_data"}
    inds = indicators_bundle(df.rename(columns={"t": "time"}))
    meta = {
        "symbol": symbol.upper(),
        "currency": None,
        "tz": "UTC",
    }
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "meta": meta,
        "t": inds["t"],
        "o": inds["o"],
        "h": inds["h"],
        "l": inds["l"],
        "c": inds["c"],
        "v": inds["v"],
        "indicators": inds["indicators"],
    }
    return out

@app.post("/v1/compute")
def v1_compute(body: OHLCIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    inds = compute_indicators(df)
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "indicators": inds,
    }
    return out
