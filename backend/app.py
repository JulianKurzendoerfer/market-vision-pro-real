import os, json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import numpy as np
import pandas as pd
from fastapi import FastAPI, Body, Query
from fastapi.middleware.cors import CORSMiddleware

from .indicators import compute_indicators

APP = FastAPI()
APP.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY: Optional[str] = os.getenv("DATA_API_KEY", None)

def _clean_list(x: pd.Series) -> list:
    return x.astype("float64").where(pd.notna(x), None).tolist()

def _to_df(d: Dict[str, Any]) -> pd.DataFrame:
    t = d.get("t", [])
    unit = "ms" if (len(t) and t[0] > 10**12) else "s"
    ts = pd.to_datetime(t, unit=unit)
    df = pd.DataFrame({
        "t": ts,
        "o": pd.Series(d.get("o", []), dtype="float64"),
        "h": pd.Series(d.get("h", []), dtype="float64"),
        "l": pd.Series(d.get("l", []), dtype="float64"),
        "c": pd.Series(d.get("c", []), dtype="float64"),
        "v": pd.Series(d.get("v", []), dtype="float64"),
    })
    return df

def _bundle(df: pd.DataFrame, meta: Optional[dict]=None) -> Dict[str, Any]:
    inds = compute_indicators(df.copy())
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": (df["t"].astype("int64")//10**6).tolist(),
        "o": _clean_list(df["o"]),
        "h": _clean_list(df["h"]),
        "l": _clean_list(df["l"]),
        "c": _clean_list(df["c"]),
        "v": _clean_list(df["v"]),
        "indicators": inds,
    }
    if meta is not None:
        out["meta"] = meta
    return out

def _fetch_json(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"ok": False, "error": f"http {e.code}"}
    except URLError as e:
        return {"ok": False, "error": f"net {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@APP.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@APP.get("/v1/bundle")
async def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={symbol}&range={range}"
    up = _fetch_json(url)
    if not isinstance(up, dict) or not up.get("t"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up,dict) else 'empty'}"}
    df = _to_df(up)
    return _bundle(df, up.get("meta", {}))

@APP.post("/v1/compute")
def v1_compute(body: Dict = Body(...)):
    d = {k: body.get(k, []) for k in ("t","o","h","l","c","v")}
    df = _to_df(d)
    if df.empty:
        return {"ok": False, "error": "empty"}
    return _bundle(df)
    
app = APP
