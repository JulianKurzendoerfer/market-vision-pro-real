import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel

from backend.indicators import compute_indicators

APP = FastAPI()

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OhlcvIn(BaseModel):
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

def _to_df(d: dict) -> pd.DataFrame:
    t = d.get("t", [])
    unit = "ms" if (max(t) if t else 0) > 10**12 else "s"
    ts = pd.to_datetime(t, unit=unit)
    df = pd.DataFrame({
        "t": t,
        "time": ts,
        "open": d.get("o", []),
        "high": d.get("h", []),
        "low": d.get("l", []),
        "close": d.get("c", []),
        "volume": d.get("v", [None]*len(t))
    })
    for col in ["open","high","low","close","volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close","high","low"]).reset_index(drop=True)
    return df

def _lists_from_df(df: pd.DataFrame):
    return {
        "t": df["t"].astype("int64").tolist(),
        "o": df["open"].astype(float).replace([np.inf, -np.inf], np.nan).where(pd.notna(df["open"]), None).tolist(),
        "h": df["high"].astype(float).replace([np.inf, -np.inf], np.nan).where(pd.notna(df["high"]), None).tolist(),
        "l": df["low"].astype(float).replace([np.inf, -np.inf], np.nan).where(pd.notna(df["low"]), None).tolist(),
        "c": df["close"].astype(float).replace([np.inf, -np.inf], np.nan).where(pd.notna(df["close"]), None).tolist(),
        "v": df["volume"].replace([np.inf, -np.inf], np.nan).where(pd.notna(df["volume"]), None).tolist()
    }

def _fetch_upstream(symbol: str, range_: str) -> dict:
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle"
    headers = {}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    with httpx.Client(timeout=30) as client:
        r = client.get(url, params={"symbol": symbol, "range": range_}, headers=headers)
        if r.status_code != 200:
            return {"ok": False, "error": f"upstream {r.status_code}", "detail": r.text[:300]}
        return r.json()

@APP.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@APP.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query("1Y")):
    up = _fetch_upstream(symbol, range)
    if not up or not up.get("ok"):
        return {"ok": False, "error": up.get("error", "no_data")}
    data = {
        "t": up.get("t", []),
        "o": up.get("o", []),
        "h": up.get("h", []),
        "l": up.get("l", []),
        "c": up.get("c", []),
        "v": up.get("v", [])
    }
    df = _to_df(data)
    inds = compute_indicators(df)
    meta = {
        "symbol": symbol.upper(),
        "currency": (up.get("meta", {}) or {}).get("currency"),
        "tz": (up.get("meta", {}) or {}).get("tz", "UTC")
    }
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "meta": meta
    }
    out.update(_lists_from_df(df))
    out["indicators"] = inds
    return out

@APP.post("/v1/compute")
def v1_compute(body: OhlcvIn = Body(...)):
    df = _to_df(body.model_dump())
    inds = compute_indicators(df)
    return {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "indicators": inds
    }

app = APP
