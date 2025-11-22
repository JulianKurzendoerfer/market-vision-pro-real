import os, json
from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from backend.indicators import compute_indicators

app = FastAPI()
DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OHLCIn(BaseModel):
    t: List[int] = []
    o: List[float] = []
    h: List[float] = []
    l: List[float] = []
    c: List[float] = []
    v: List[float] = []

def _to_df(d: Dict[str, Any]) -> pd.DataFrame:
    ts = pd.Series(d.get("t", []), dtype="int64")
    unit = "ms" if len(ts) and (ts.iloc[0] > 10**12 or ts.iloc[0] < 0) else "s"
    idx = pd.to_datetime(ts, unit=unit, utc=True)
    df = pd.DataFrame({
        "t": idx,
        "o": pd.Series(d.get("o", []), dtype="float64"),
        "h": pd.Series(d.get("h", []), dtype="float64"),
        "l": pd.Series(d.get("l", []), dtype="float64"),
        "c": pd.Series(d.get("c", []), dtype="float64"),
        "v": pd.Series(d.get("v", []), dtype="float64"),
    })
    return df

def _bundle(df: pd.DataFrame) -> Dict[str, Any]:
    inds = compute_indicators(df)
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": [int(x.timestamp()*1000) for x in df["t"]],
        "o": pd.Series(df["o"], dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "h": pd.Series(df["h"], dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "l": pd.Series(df["l"], dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "c": pd.Series(df["c"], dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "v": pd.Series(df["v"], dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "indicators": inds,
    }
    return out

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={symbol}&range={range}"
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return {"ok": False, "error": f"http {resp.status_code}"}
            up = resp.json()
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    if not isinstance(up, dict) or not up.get("t"):
        return {"ok": False, "error": "upstream empty"}
    df = _to_df(up)
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: OHLCIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    if df.empty:
        return {"ok": False, "error": "empty"}
    return _bundle(df)
