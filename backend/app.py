import os, json
from typing import Dict, List, Optional
from datetime import datetime, timezone
from urllib.parse import quote
import pandas as pd
import httpx
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from backend.indicators import compute_indicators

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
DATA_API_KEY = os.getenv("DATA_API_KEY", "")

def _to_df(d: Dict) -> pd.DataFrame:
    t = d.get("t", [])
    unit = "ms" if len(t) and max(t) > 10**12 else "s"
    ts = pd.to_datetime(t, unit=unit, utc=True) if len(t) else []
    df = pd.DataFrame({
        "t": ts,
        "o": d.get("o", []),
        "h": d.get("h", []),
        "l": d.get("l", []),
        "c": d.get("c", []),
        "v": d.get("v", []),
    })
    return df

def _bundle(df: pd.DataFrame) -> Dict:
    inds = compute_indicators(df.rename(columns={"t":"time"}))
    out = {
        "ok": True,
        "asof": datetime.now(timezone.utc).isoformat(),
        "t": [int(x.timestamp()*1000) for x in df["t"]] if "t" in df else [],
        "o": pd.Series(df["o"], dtype="float64").replace([pd.NA, float("inf"), float("-inf")], None).tolist() if "o" in df else [],
        "h": pd.Series(df["h"], dtype="float64").replace([pd.NA, float("inf"), float("-inf")], None).tolist() if "h" in df else [],
        "l": pd.Series(df["l"], dtype="float64").replace([pd.NA, float("inf"), float("-inf")], None).tolist() if "l" in df else [],
        "c": pd.Series(df["c"], dtype="float64").replace([pd.NA, float("inf"), float("-inf")], None).tolist() if "c" in df else [],
        "v": pd.Series(df["v"], dtype="float64").replace([pd.NA, float("inf"), float("-inf")], None).tolist() if "v" in df else [],
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
    headers = {"User-Agent": "mvp-backend/1.0"}
    if DATA_API_KEY:
        headers["X-API-KEY"] = DATA_API_KEY
    try:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers)
        if resp.status_code != 200:
            return {"ok": False, "error": f"http {resp.status_code}"}
        up = resp.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if not up or not up.get("t"):
        return {"ok": False, "error": "upstream empty"}
    df = _to_df(up)
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: Dict = Body(...)):
    d = {k: body.get(k, []) for k in ("t","o","h","l","c","v")}
    df = _to_df(d)
    return _bundle(df)
