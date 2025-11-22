import os, json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel

from backend.indicators import compute_indicators

app = FastAPI()

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OHLCIn(BaseModel):
    t: Optional[List[int]] = None
    o: Optional[List[float]] = None
    h: Optional[List[float]] = None
    l: Optional[List[float]] = None
    c: Optional[List[float]] = None
    v: Optional[List[float]] = None

def _to_df(d: Dict) -> pd.DataFrame:
    t = d.get("t", [])
    o = d.get("o", [])
    h = d.get("h", [])
    l = d.get("l", [])
    c = d.get("c", [])
    v = d.get("v", [])
    if len(t) == 0:
        return pd.DataFrame(columns=list("tohlcv"))
    ts = pd.Series(t)
    if ts.max() < 10**12:
        ts = ts * 1000
    df = pd.DataFrame({
        "t": pd.to_datetime(ts, unit="ms"),
        "o": o, "h": h, "l": l, "c": c, "v": v
    })
    df = df.dropna(subset=["c"]).reset_index(drop=True)
    return df

def _fetch_json(url: str) -> Dict:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _bundle(df: pd.DataFrame) -> Dict:
    inds = compute_indicators(df.copy())
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": [int(x.timestamp()*1000) for x in df["t"]] if "t" in df else [],
        "o": pd.Series(df.get("o", [])).astype("float64").replace([np.inf,-np.inf], np.nan).where(pd.notna(df.get("o", [])), None).tolist() if "o" in df else [],
        "h": pd.Series(df.get("h", [])).astype("float64").replace([np.inf,-np.inf], np.nan).where(pd.notna(df.get("h", [])), None).tolist() if "h" in df else [],
        "l": pd.Series(df.get("l", [])).astype("float64").replace([np.inf,-np.inf], np.nan).where(pd.notna(df.get("l", [])), None).tolist() if "l" in df else [],
        "c": pd.Series(df.get("c", [])).astype("float64").replace([np.inf,-np.inf], np.nan).where(pd.notna(df.get("c", [])), None).tolist() if "c" in df else [],
        "v": pd.Series(df.get("v", [])).astype("float64").replace([np.inf,-np.inf], np.nan).where(pd.notna(df.get("v", [])), None).tolist() if "v" in df else [],
        "indicators": inds
    }
    return out

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={symbol}&range={range}"
    up = _fetch_json(url)
    if not isinstance(up, dict) or not up.get("t"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up,dict) else 'empty'}"}
    df = _to_df(up)
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: OHLCIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    if df.empty:
        return {"ok": False, "error": "empty"}
    return _bundle(df)
