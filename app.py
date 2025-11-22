import os, json
from datetime import datetime, timezone
from typing import List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel

from indicators import compute_indicators

app = FastAPI()

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OhlcvIn(BaseModel):
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

def _to_df(d: dict) -> pd.DataFrame:
    ts = d.get("t", [])
    unit = "ms" if (max(ts) if ts else 0) > 10**12 else "s"
    t = pd.to_datetime(ts, unit=unit)
    return pd.DataFrame({"t": t, "o": d.get("o", []), "h": d.get("h", []), "l": d.get("l", []), "c": d.get("c", []), "v": d.get("v", [])})

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

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

def _bundle_response(df: pd.DataFrame) -> dict:
    inds = compute_indicators(df.copy())
    t_ms = (df["t"].astype("int64") // 10**6).tolist()
    return {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": t_ms,
        "o": pd.Series(df["o"]).tolist(),
        "h": pd.Series(df["h"]).tolist(),
        "l": pd.Series(df["l"]).tolist(),
        "c": pd.Series(df["c"]).tolist(),
        "v": pd.Series(df["v"]).tolist(),
        "indicators": inds,
    }

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = _fetch_json(url)
    if not up.get("ok"):
        return {"ok": False, "error": f"upstream {up.get('error', '')}"}
    d = {"t": up.get("t", []), "o": up.get("o", []), "h": up.get("h", []), "l": up.get("l", []), "c": up.get("c", []), "v": up.get("v", [])}
    df = _to_df(d)
    return _bundle_response(df)

@app.post("/v1/compute")
def v1_compute(body: OhlcvIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    inds = compute_indicators(df)
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat(), "indicators": inds}
