import os, json
from datetime import datetime, timezone
from typing import List, Optional
import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OhclIn(BaseModel):
    t: Optional[List[int]] = None
    o: Optional[List[float]] = None
    h: Optional[List[float]] = None
    l: Optional[List[float]] = None
    c: Optional[List[float]] = None
    v: Optional[List[float]] = None

def _clean_list(x: pd.Series):
    y = x.astype("float64").replace([np.inf, -np.inf], np.nan).round(6)
    return [None if pd.isna(v) else float(v) for v in y.to_numpy()]

def _to_df(d: dict) -> pd.DataFrame:
    t = d.get("t", []) or []
    unit = "ms" if (len(t) and max(t) > 10**12) else "s"
    df = pd.DataFrame({
        "t": d.get("t", []) or [],
        "o": d.get("o", []) or [],
        "h": d.get("h", []) or [],
        "l": d.get("l", []) or [],
        "c": d.get("c", []) or [],
        "v": d.get("v", []) or [],
    })
    if len(df):
        df["t"] = pd.to_datetime(df["t"], unit=unit)
    return df

def _bundle(df: pd.DataFrame) -> dict:
    inds = compute_indicators({
        "c": df["c"].astype("float64").tolist(),
        "h": df["h"].astype("float64").tolist(),
        "l": df["l"].astype("float64").tolist(),
    })
    return {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": _clean_list(pd.Series(df["t"].astype("int64") // 10**9 * 10**9)),
        "o": _clean_list(pd.Series(df["o"])),
        "h": _clean_list(pd.Series(df["h"])),
        "l": _clean_list(pd.Series(df["l"])),
        "c": _clean_list(pd.Series(df["c"])),
        "v": _clean_list(pd.Series(df["v"])),
        "indicators": inds,
    }

async def _get_json(url: str) -> dict:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            return {"ok": False, "error": f"http {r.status_code}"}
        return r.json()

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={symbol}&range={range}"
    up = await _get_json(url)
    if not up or not up.get("t"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up, dict) else 'empty'}"}
    df = _to_df(up)
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: OhclIn = Body(...)):
    d = {k: getattr(body, k) for k in ["t","o","h","l","c","v"]}
    df = _to_df(d)
    return _bundle(df)
