import os, json
from datetime import datetime, timezone
from typing import List, Optional, Dict
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from .indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

def _fetch_json(url: str) -> Dict:
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

class OhlcvIn(BaseModel):
    t: Optional[List[int]] = None
    o: Optional[List[float]] = None
    h: Optional[List[float]] = None
    l: Optional[List[float]] = None
    c: List[float]
    v: Optional[List[float]] = None

def _to_df(d: Dict) -> pd.DataFrame:
    t = d.get("t", [])
    unit = "ms" if (len(t) and max(t) > 10**12) else "s"
    ts = pd.to_datetime(t, unit=unit) if t else None
    return pd.DataFrame({"t": ts, "o": d.get("o", []), "h": d.get("h", []), "l": d.get("l", []), "c": d.get("c", []), "v": d.get("v", [])})

def _bundle(df: pd.DataFrame) -> Dict:
    inds = compute_indicators(df.copy())
    return {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": [int(x.timestamp()*1000) for x in df["t"]] if "t" in df and df["t"].notna().any() else [],
        "o": pd.Series(df["o"], dtype="float64").replace([pd.NA, np.inf, -np.inf], None).tolist() if "o" in df else [],
        "h": pd.Series(df["h"], dtype="float64").replace([pd.NA, np.inf, -np.inf], None).tolist() if "h" in df else [],
        "l": pd.Series(df["l"], dtype="float64").replace([pd.NA, np.inf, -np.inf], None).tolist() if "l" in df else [],
        "c": pd.Series(df["c"], dtype="float64").replace([pd.NA, np.inf, -np.inf], None).tolist(),
        "v": pd.Series(df["v"], dtype="float64").replace([pd.NA, np.inf, -np.inf], None).tolist() if "v" in df else [],
        "indicators": inds
    }

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query(...)):
    if not DATA_API_BASE:
        return {"ok": False, "error": "DATA_API_BASE not set"}
    url = f"{DATA_API_BASE}/v1/bundle?symbol={quote(symbol)}&range={range}"
    up = _fetch_json(url)
    if not isinstance(up, dict) or not up.get("t"):
        return {"ok": False, "error": f"upstream {up.get('error') if isinstance(up, dict) else 'empty'}"}
    df = _to_df(up)
    out = _bundle(df)
    out["meta"] = up.get("meta", {})
    return out

@app.post("/v1/compute")
def v1_compute(body: OhlcvIn = Body(...)):
    df = _to_df(body.model_dump())
    return _bundle(df)
