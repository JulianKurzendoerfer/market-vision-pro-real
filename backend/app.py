import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd
import httpx
from fastapi import FastAPI, Query, Body

from backend.indicators import compute_indicators

app = FastAPI()

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

def _to_df(d: Dict) -> pd.DataFrame:
    t = d.get("t", [])
    unit = "ms" if (max(t) if t else 0) > 10**12 else "s"
    ts = pd.to_datetime(t, unit=unit)
    df = pd.DataFrame({
        "t": ts,
        "o": d.get("o", []),
        "h": d.get("h", []),
        "l": d.get("l", []),
        "c": d.get("c", []),
        "v": d.get("v", []),
    })
    return df

def _bundle(df: pd.DataFrame) -> Dict:
    inds = compute_indicators(df.rename(columns={"t":"time"}))
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": [int(x.timestamp()*1000) for x in df["t"]],
        "o": pd.Series(df["o"], dtype="float64").replace([pd.NA], 0).tolist(),
        "h": pd.Series(df["h"], dtype="float64").replace([pd.NA], 0).tolist(),
        "l": pd.Series(df["l"], dtype="float64").replace([pd.NA], 0).tolist(),
        "c": pd.Series(df["c"], dtype="float64").replace([pd.NA], 0).tolist(),
        "v": pd.Series(df["v"], dtype="float64").replace([pd.NA], 0).tolist(),
        "indicators": inds,
    }
    return out

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

async def _fetch_json(url: str) -> Dict:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            return {"ok": False, "error": f"http {r.status_code}"}
        try:
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    from urllib.parse import quote
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = await _fetch_json(url)
    if not isinstance(up, dict) or not up.get("ok"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up,dict) else 'empty'}"}
    df = _to_df(up)
    out = _bundle(df)
    out["meta"] = up.get("meta", {})
    return out

@app.post("/v1/compute")
def v1_compute(body: Dict = Body(...)):
    d = body
    df = _to_df(d)
    if df.empty:
        return {"ok": False, "error": "empty"}
    return _bundle(df)
