import os, json
import pandas as pd
from datetime import datetime, timezone
from typing import List, Optional
from urllib.request import Request, urlopen
from urllib.parse import quote
from urllib.error import HTTPError, URLError
from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from indicators import compute_indicators

APP = FastAPI()
DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

class OhlcIn(BaseModel):
    t: List[int]
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    v: Optional[List[float]] = None

def _fetch_json(url: str) -> dict:
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        return {"ok": False, "error": f"http {e.code}"}
    except URLError as e:
        return {"ok": False, "error": f"net {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _to_df(d: dict) -> pd.DataFrame:
    t = d.get("t", [])
    o = d.get("o", [])
    h = d.get("h", [])
    l = d.get("l", [])
    c = d.get("c", [])
    v = d.get("v", [])
    n = min(len(t), len(o), len(h), len(l), len(c)) if t else 0
    t = t[:n]; o = o[:n]; h = h[:n]; l = l[:n]; c = c[:n]; v = (v[:n] if v else [None]*n)
    unit = "ms" if (max(t) if t else 0) > 10**12 else "s"
    ts = pd.to_datetime(t, unit=unit, utc=True)
    df = pd.DataFrame({"t": ts, "o": o, "h": h, "l": l, "c": c, "v": v})
    return df

def _bundle_response(df: pd.DataFrame) -> dict:
    inds = compute_indicators(df.copy())
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": (df["t"].astype("int64")//10**6).tolist(),
        "o": df["o"].tolist(),
        "h": df["h"].tolist(),
        "l": df["l"].tolist(),
        "c": df["c"].tolist(),
        "v": df["v"].tolist(),
        "indicators": inds,
    }
    return out

@APP.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@APP.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={quote(range)}"
    up = _fetch_json(url)
    if not up.get("ok"):
        return {"ok": False, "error": f"upstream {up.get('error')}"}
    df = _to_df(up)
    return _bundle_response(df)

@APP.post("/v1/compute")
def v1_compute(body: OhlcIn = Body(...)):
    d = body.model_dump()
    df = _to_df(d)
    inds = compute_indicators(df)
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat(), "indicators": inds}
