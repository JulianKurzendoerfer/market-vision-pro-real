import os, json
from datetime import datetime, timezone
from typing import Dict, Optional, List
import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from backend.indicators import compute_indicators

app = FastAPI()
DATA_API_BASE = os.getenv("DATA_API_BASE","").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY","")

class OhlcIn(BaseModel):
    t: Optional[List[int]] = None
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

def _to_df(d: Dict) -> pd.DataFrame:
    cols = ["t","o","h","l","c","v"]
    data = {k: d.get(k, []) for k in cols}
    df = pd.DataFrame(data)
    if "t" in df and not df["t"].empty:
        df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True, errors="coerce")
    return df

def _clean(s: pd.Series) -> list:
    return s.astype("float64").replace([np.inf, -np.inf], np.nan).where(~s.isna(), np.nan).replace({np.nan: None}).tolist()

def _bundle(df: pd.DataFrame, meta: Dict = None) -> Dict:
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": [int(x.timestamp()*1000) for x in df.get("t", pd.Series([], dtype="datetime64[ns, UTC]")).fillna(pd.NaT)],
        "o": _clean(df.get("o", pd.Series([], dtype="float64"))),
        "h": _clean(df.get("h", pd.Series([], dtype="float64"))),
        "l": _clean(df.get("l", pd.Series([], dtype="float64"))),
        "c": _clean(df.get("c", pd.Series([], dtype="float64"))),
        "v": _clean(df.get("v", pd.Series([], dtype="float64"))),
        "indicators": compute_indicators(df[["o","h","l","c","v"]].copy() if not df.empty else pd.DataFrame(columns=["o","h","l","c","v"])),
        "meta": meta or {},
    }
    return out

async def _fetch_json(url: str) -> Dict:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            return {"ok": False, "error": f"http {r.status_code}"}
        try:
            return r.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    from urllib.parse import quote
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = await _fetch_json(url)
    if not isinstance(up, dict) or not up.get("ok"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up, dict) else 'error'}"}
    df = _to_df(up)
    return _bundle(df, up.get("meta", {}))

@app.post("/v1/compute")
def v1_compute(body: OhlcIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    return _bundle(df)
