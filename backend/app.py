import os, json
from datetime import datetime, timezone
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import quote
from backend.indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_API_BASE = os.getenv("DATA_API_BASE","").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY","")

def _to_df(d: Dict) -> pd.DataFrame:
    cols = ["t","o","h","l","c","v"]
    d2 = {k: d.get(k, []) for k in cols}
    df = pd.DataFrame(d2)
    if df.empty:
        return df
    if np.issubdtype(df["t"].dtype, np.number):
        pass
    else:
        with np.errstate(all="ignore"):
            df["t"] = pd.to_numeric(df["t"], errors="coerce")
    return df

def _bundle(df: pd.DataFrame) -> Dict:
    inds = compute_indicators(df.rename(columns={"t":"time"}))
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": df["t"].astype("int64").replace({np.nan: None}).tolist(),
        "o": pd.Series(df["o"], dtype="float64").replace({np.nan: None}).tolist(),
        "h": pd.Series(df["h"], dtype="float64").replace({np.nan: None}).tolist(),
        "l": pd.Series(df["l"], dtype="float64").replace({np.nan: None}).tolist(),
        "c": pd.Series(df["c"], dtype="float64").replace({np.nan: None}).tolist(),
        "v": pd.Series(df["v"], dtype="float64").replace({np.nan: None}).tolist(),
        "indicators": inds,
    }
    return out

async def _get_json(url: str) -> Dict:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return {"ok": False, "error": f"http {resp.status_code}"}
        try:
            return resp.json()
        except Exception as e:
            return {"ok": False, "error": f"json {e}"}

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = await _get_json(url)
    if not isinstance(up, dict):
        return {"ok": False, "error": "upstream invalid"}
    df = _to_df(up if {"t","o","h","l","c","v"}.issubset(up.keys()) else up.get("data", {}))
    if df.empty:
        return {"ok": False, "error": "upstream empty", "meta": up.get("meta", {})}
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: Dict = Body(...)):
    df = _to_df(body)
    if df.empty:
        return {"ok": False, "error": "empty"}
    inds = compute_indicators(df)
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat(), "indicators": inds}
