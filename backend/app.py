import os, json
from datetime import datetime, timezone
from typing import List
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from backend.indicators import compute_indicators

app = FastAPI()

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OhlcvIn(BaseModel):
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: List[float]

def _to_df(d: dict) -> pd.DataFrame:
    t = d.get("t", [])
    unit = "ms" if (t and max(t) > 10**11) else "s"
    ts = pd.to_datetime(t, unit=unit, utc=True)
    def f(x):
        try:
            return float(x)
        except Exception:
            return np.nan
    return pd.DataFrame({
        "t": ts,
        "o": [f(x) for x in d.get("o", [])],
        "h": [f(x) for x in d.get("h", [])],
        "l": [f(x) for x in d.get("l", [])],
        "c": [f(x) for x in d.get("c", [])],
        "v": [f(x) for x in d.get("v", [])],
    })

def _fetch_json(url: str) -> dict:
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

def _clean_list(s: pd.Series):
    out = []
    a = s.to_numpy(dtype=float, copy=False)
    for x in a:
        if x is None or np.isnan(x) or np.isinf(x):
            out.append(None)
        else:
            out.append(float(x))
    return out

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

def _bundle_response(df: pd.DataFrame) -> dict:
    inds = compute_indicators(df.copy())
    tms = (df["t"].astype("int64") // 10**6).tolist()
    return {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": tms,
        "o": _clean_list(df["o"]),
        "h": _clean_list(df["h"]),
        "l": _clean_list(df["l"]),
        "c": _clean_list(df["c"]),
        "v": _clean_list(df["v"]),
        "indicators": inds,
    }

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = _fetch_json(url)
    if not up or not up.get("t"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up, dict) else 'invalid'}"}
    df = _to_df(up)
    return _bundle_response(df)

@app.post("/v1/compute")
def v1_compute(body: OhlcvIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    inds = compute_indicators(df)
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat(), "indicators": inds}
