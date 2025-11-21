import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx
import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel

from indicators import compute

app = FastAPI()

class OhlcvIn(BaseModel):
    meta: Optional[Dict] = None
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: List[float]

def _to_df(d: Dict) -> pd.DataFrame:
    return pd.DataFrame({
        "t": d.get("t", []),
        "open": d.get("o", []),
        "high": d.get("h", []),
        "low": d.get("l", []),
        "close": d.get("c", []),
        "volume": d.get("v", []),
    })

def fetch_ohlc(symbol: str, range: str) -> Dict:
    base = os.getenv("DATA_API_BASE", "").rstrip("/")
    if not base:
        return {"ok": False, "error": "DATA_API_BASE missing"}
    url = f"{base}/v1/bundle"
    headers = {}
    key = os.getenv("DATA_API_KEY")
    if key: headers["X-API-KEY"] = key
    params = {"symbol": symbol, "range": range}
    with httpx.Client(timeout=20.0) as client:
        r = client.get(url, params=params, headers=headers)
        r.raise_for_status()
        j = r.json()
    if not j or not j.get("ok"):
        return {"ok": False, "error": "upstream_no_ok"}
    return {
        "ok": True,
        "meta": j.get("meta", {}),
        "t": j.get("t", []),
        "o": j.get("o", []),
        "h": j.get("h", []),
        "l": j.get("l", []),
        "c": j.get("c", []),
        "v": j.get("v", []),
    }

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    d = fetch_ohlc(symbol, range)
    if not d.get("ok"):
        return {"ok": False, "error": d.get("error", "fetch_failed")}
    df = _to_df(d)
    inds = compute(df.rename(columns={"t":"time"}))
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
def v1_compute(body: OhlcvIn):
    d = body.model_dump()
    df = _to_df(d)
    inds = compute(df.rename(columns={"t":"time"}))
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "indicators": inds,
    }
    return out
