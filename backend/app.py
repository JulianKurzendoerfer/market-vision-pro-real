import os, json
from datetime import datetime, timezone
from typing import List, Optional
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from .indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

def _fetch_json(url: str) -> dict:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    try:
        with urlopen(Request(url, headers=headers), timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"ok": False, "error": f"http:{e.code}"}
    except URLError as e:
        return {"ok": False, "error": f"net:{getattr(e, 'reason', 'err')}"}
    except Exception as e:
        return {"ok": False, "error": f"err:{e}"}

def _to_df(d: dict) -> pd.DataFrame:
    t = d.get("t", [])
    o = d.get("o", [])
    h = d.get("h", [])
    l = d.get("l", [])
    c = d.get("c", [])
    v = d.get("v", [])
    df = pd.DataFrame({"t": t, "o": o, "h": h, "l": l, "c": c, "v": v})
    return df

def _bundle_response(df: pd.DataFrame) -> dict:
    inds = compute_indicators({"c": df["c"], "h": df["h"], "l": df["l"]})
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": df.get("t", pd.Series([], dtype="float64")).astype("int64").tolist() if "t" in df else [],
        "o": pd.Series(df.get("o", []), dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "h": pd.Series(df.get("h", []), dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "l": pd.Series(df.get("l", []), dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "c": pd.Series(df.get("c", []), dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "v": pd.Series(df.get("v", []), dtype="float64").replace([np.inf, -np.inf], np.nan).tolist(),
        "indicators": inds,
    }
    return out

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = _fetch_json(url)
    if not up or ("t" not in up and not up.get("ok", False)):
        return {"ok": False, "error": f"upstream {up.get('error','invalid') if isinstance(up,dict) else 'invalid'}"}
    df = _to_df(up if isinstance(up, dict) else {})
    return _bundle_response(df)

class OhlcIn(Body):
    t: Optional[List[int]] = None
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

@app.post("/v1/compute")
def v1_compute(body: dict = Body(...)):
    d = body
    df = _to_df(d)
    inds = compute_indicators({"c": df["c"], "h": df["h"], "l": df["l"]})
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat(), "indicators": inds}
