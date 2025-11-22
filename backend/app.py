import os, json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OhlcIn(BaseModel):
    t: Optional[List[int]] = None
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

async def _get_json(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, headers=headers)
    if r.status_code != 200:
        return {"ok": False, "error": f"http {r.status_code}"}
    try:
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _to_df(d: Dict[str, Any]) -> pd.DataFrame:
    cols = {k: d.get(k, []) for k in ("t","o","h","l","c","v")}
    df = pd.DataFrame(cols)
    if "t" in df.columns and len(df["t"]) and df["t"].max() < 1e12:
        df["t"] = (df["t"].astype("int64") * 1000).astype("int64")
    return df

def _bundle(df: pd.DataFrame) -> Dict[str, Any]:
    inds = compute_indicators(df.copy())
    out = {
        "ok": True,
        "asof": _now(),
        "t": df["t"].astype("int64").tolist() if "t" in df else [],
        "o": pd.Series(df["o"], dtype="float64").tolist(),
        "h": pd.Series(df["h"], dtype="float64").tolist(),
        "l": pd.Series(df["l"], dtype="float64").tolist(),
        "c": pd.Series(df["c"], dtype="float64").tolist(),
        "v": pd.Series(df["v"], dtype="float64").tolist() if "v" in df else [],
        "indicators": inds,
    }
    return out

@app.get("/health")
def health():
    return {"ok": True, "asof": _now()}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    from urllib.parse import quote
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = await _get_json(url)
    if not up or not up.get("t"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up,dict) else 'empty'}"}
    df = _to_df(up)
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: Dict = Body(...)):
    d = {k: body.get(k, []) for k in ("t","o","h","l","c","v")}
    df = _to_df(d)
    return _bundle(df)
