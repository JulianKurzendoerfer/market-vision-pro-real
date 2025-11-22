import os, json
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime, timezone
from typing import List, Optional
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from backend.indicators import compute_indicators

APP = FastAPI()
DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OhlcvIn(BaseModel):
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

def _clean_list(x: pd.Series) -> list:
    x = x.replace([np.inf, -np.inf], np.nan)
    return [None if pd.isna(v) else float(v) for v in x]

def _to_df(d: dict) -> pd.DataFrame:
    t = d.get("t", []) or []
    unit = "ms" if (len(t) and max(t) > 10**12) else "s"
    ts = pd.to_datetime(t, unit=unit, utc=True)
    df = pd.DataFrame({
        "t": ts,
        "open": d.get("o", []),
        "high": d.get("h", []),
        "low": d.get("l", []),
        "close": d.get("c", []),
        "volume": d.get("v", []) if d.get("v") is not None else [None]*len(ts),
    })
    return df

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

@APP.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

def _bundle_response(df: pd.DataFrame) -> dict:
    inds = compute_indicators(df.copy())
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": (df["t"].astype("int64")//10**6).tolist(),
        "o": _clean_list(pd.Series(df["open"])),
        "h": _clean_list(pd.Series(df["high"])),
        "l": _clean_list(pd.Series(df["low"])),
        "c": _clean_list(pd.Series(df["close"])),
        "v": _clean_list(pd.Series(df["volume"])) if "volume" in df else [],
        "indicators": {k: _clean_list(pd.Series(v)) for k, v in inds.items()},
    }
    return out

@APP.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = _fetch_json(url)
    if not up.get("ok"):
        return {"ok": False, "error": up.get("error", "upstream_error")}
    df = _to_df(up)
    if df.empty:
        return {"ok": False, "error": "no_data"}
    return _bundle_response(df)

@APP.post("/v1/compute")
def v1_compute(body: OhlcvIn = Body(...)):
    df = _to_df(body.model_dump())
    if df.empty:
        return {"ok": False, "error": "no_data"}
    return _bundle_response(df)

app = APP
