import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel

from indicators import compute_bundle

app = FastAPI()

DATA_API_BASE = os.getenv("DATA_API_BASE", "https://market-vision-pro-real.onrender.com")
DATA_API_KEY = os.getenv("DATA_API_KEY")

def _headers() -> Dict[str, str]:
    h = {}
    if DATA_API_KEY:
        h["X-API-KEY"] = DATA_API_KEY
        h["Authorization"] = DATA_API_KEY
    return h

class OhlcvIn(BaseModel):
    t: List[Any]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None
    meta: Optional[Dict[str, Any]] = None

def _to_df(d: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame({
        "t": d.get("t", []),
        "open": d.get("o", []),
        "high": d.get("h", []),
        "low": d.get("l", []),
        "close": d.get("c", []),
        "volume": d.get("v", []),
    })
    return df

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    async with httpx.AsyncClient(base_url=DATA_API_BASE, timeout=30.0) as client:
        r = await client.get("/v1/bundle", params={"symbol": symbol, "range": range}, headers=_headers())
        r.raise_for_status()
        d = r.json()
    return d

@app.get("/v1/compute")
async def v1_compute(symbol: str = Query(...), range: str = Query(...)):
    async with httpx.AsyncClient(base_url=DATA_API_BASE, timeout=30.0) as client:
        r = await client.get("/v1/bundle", params={"symbol": symbol, "range": range}, headers=_headers())
        r.raise_for_status()
        d = r.json()
    df = _to_df(d)
    inds = compute_bundle(df.rename(columns={"t": "time"}))
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "meta": d.get("meta", {}),
        "t": d.get("t", []),
        "o": d.get("o", []),
        "h": d.get("h", []),
        "l": d.get("l", []),
        "c": d.get("c", []),
        "v": d.get("v", []),
        "indicators": inds,
    }
    return out

@app.post("/v1/compute")
def v1_compute_post(body: OhlcvIn):
    d = body.model_dump()
    df = _to_df(d)
    inds = compute_bundle(df.rename(columns={"t": "time"}))
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "meta": d.get("meta", {}),
        "t": d.get("t", []),
        "o": d.get("o", []),
        "h": d.get("h", []),
        "l": d.get("l", []),
        "c": d.get("c", []),
        "v": d.get("v", []),
        "indicators": inds,
    }
    return out
