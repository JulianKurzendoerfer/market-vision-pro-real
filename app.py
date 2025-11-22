import os, json
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import httpx
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware

from indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

def _now():
    return datetime.now(timezone.utc).isoformat()

def _to_df(d: Dict) -> pd.DataFrame:
    cols = ["t","o","h","l","c","v"]
    data = {k: d.get(k, []) for k in cols}
    return pd.DataFrame(data, columns=cols)

def _clean_list(s: pd.Series) -> List[Optional[float]]:
    a = s.to_numpy(dtype="float64", copy=False)
    a[~np.isfinite(a)] = np.nan
    return pd.Series(a, dtype="float64").where(pd.notna(a), None).tolist()

async def _get_json(url: str) -> Dict:
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

def _bundle(df: pd.DataFrame) -> Dict:
    inds = compute_indicators(df.copy())
    out = {
        "ok": True,
        "asof": _now(),
        "t": _clean_list(pd.Series(df["t"], dtype="float64")),
        "o": _clean_list(pd.Series(df["o"], dtype="float64")),
        "h": _clean_list(pd.Series(df["h"], dtype="float64")),
        "l": _clean_list(pd.Series(df["l"], dtype="float64")),
        "c": _clean_list(pd.Series(df["c"], dtype="float64")),
        "v": _clean_list(pd.Series(df["v"], dtype="float64")),
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
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote_plus(symbol)}&range={quote_plus(range)}"
    up = await _get_json(url)
    if not up or not up.get("ok"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up, dict) else 'invalid'}"}
    df = _to_df(up)
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: Dict = Body(...)):
    d = {k: body.get(k, []) for k in ("t","o","h","l","c","v")}
    df = _to_df(d)
    inds = compute_indicators(df)
    return {"ok": True, "asof": _now(), "indicators": inds}
