import os, json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel

from backend.indicators import compute_indicators

APP = FastAPI()

DATA_API_BASE = os.getenv("DATA_API_BASE","").rstrip("/")
DATA_API_KEY  = os.getenv("DATA_API_KEY","")

class OHLCIn(BaseModel):
    t: Optional[List[int]] = None
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

def _clean_list(s: pd.Series) -> list:
    return [None if pd.isna(x) else float(x) for x in s]

def _to_df(d: Dict[str, Any]) -> pd.DataFrame:
    df = pd.DataFrame({
        "t": d.get("t", []),
        "o": d.get("o", []),
        "h": d.get("h", []),
        "l": d.get("l", []),
        "c": d.get("c", []),
        "v": d.get("v", []),
    })
    # Ensure numeric dtype
    for col in ["o","h","l","c","v"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def _bundle(df: pd.DataFrame) -> Dict[str, Any]:
    inds = compute_indicators(df.copy())
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": df.get("t", pd.Series([], dtype="int64")).astype("Int64").tolist() if "t" in df else [],
        "o": _clean_list(df["o"]) if "o" in df else [],
        "h": _clean_list(df["h"]) if "h" in df else [],
        "l": _clean_list(df["l"]) if "l" in df else [],
        "c": _clean_list(df["c"]) if "c" in df else [],
        "v": _clean_list(df["v"]) if "v" in df else [],
        "indicators": inds,
    }
    return out

def _fetch_json(url: str) -> Dict[str, Any]:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as resp:
            if resp.status != 200:
                return {"ok": False, "error": f"http {resp.status}"}
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
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = _fetch_json(url)
    if not isinstance(up, dict) or not up.get("ok"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up, dict) else 'empty'}"}
    df = _to_df(up)
    if df.empty or not all(c in df for c in ["o","h","l","c"]):
        return {"ok": False, "error": "empty"}
    return _bundle(df)

@APP.post("/v1/compute")
def v1_compute(body: OHLCIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    if df.empty or not all(c in df for c in ["o","h","l","c"]):
        return {"ok": False, "error": "empty"}
    return _bundle(df)
