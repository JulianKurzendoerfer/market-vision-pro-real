import os, json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import quote

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
    o: Optional[List[float]] = None
    h: Optional[List[float]] = None
    l: Optional[List[float]] = None
    c: Optional[List[float]] = None
    v: Optional[List[float]] = None

def _to_df(d: Dict) -> pd.DataFrame:
    t = d.get("t", [])
    unit = "ms" if (len(t) and max(t) > 10**12) else "s"
    idx = pd.to_datetime(t, unit=unit) if len(t) else pd.Index([])
    df = pd.DataFrame({
        "t": idx,
        "o": d.get("o", []),
        "h": d.get("h", []),
        "l": d.get("l", []),
        "c": d.get("c", []),
        "v": d.get("v", []),
    })
    return df

def _bundle(df: pd.DataFrame) -> Dict:
    inds = compute_indicators(df.rename(columns={"t":"time"}).set_index("time"))
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": [int(x.timestamp()*1000) for x in df["t"]] if "t" in df else [],
        "o": df["o"].astype("float64").replace([pd.NA, np.inf, -np.inf], np.nan).tolist(),
        "h": df["h"].astype("float64").replace([pd.NA, np.inf, -np.inf], np.nan).tolist(),
        "l": df["l"].astype("float64").replace([pd.NA, np.inf, -np.inf], np.nan).tolist(),
        "c": df["c"].astype("float64").replace([pd.NA, np.inf, -np.inf], np.nan).tolist(),
        "v": df["v"].astype("float64").replace([pd.NA, np.inf, -np.inf], np.nan).tolist(),
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
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
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
        return {"ok": False, "error": str(e)}
    if not isinstance(up, dict) or not up.get("t"):
        return {"ok": False, "error": "upstream empty"}
    df = _to_df(up)
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: OhlcIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    if df.empty:
        return {"ok": False, "error": "empty"}
    return _bundle(df)
