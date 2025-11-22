from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import os, requests
import pandas as pd
from indicators import compute_indicators

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
API_KEY  = os.getenv("DATA_API_KEY", "")

def _fetch(symbol: str, range: str = "1Y", interval: str = "1d", adj: bool = True):
    if not API_BASE:
        return None
    params = {"s": symbol, "a": "split,div,ohlc", "i": interval, "r": range, "adj": "1" if adj else "0"}
    headers = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}
    try:
        r = requests.get(f"{API_BASE}/bundle", params=params, headers=headers, timeout=30)
        r.raise_for_status()
        js = r.json()
        ohlc = js.get("ohlc") or js
        if not ohlc:
            return None
        df = pd.DataFrame(ohlc)
        if {"Open","High","Low","Close","Date"}.issubset(df.columns):
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
        return df
    except Exception:
        return None

def _df_from_ohlc(ohlc):
    if not ohlc:
        return pd.DataFrame()
    df = pd.DataFrame(ohlc)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
    return df

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
def bundle(symbol: str, range: str = "1Y", interval: str = "1d", adj: bool = True):
    if not API_BASE:
        return {"ok": False, "error": "DATA_API_BASE missing"}
    data = _fetch(symbol, range, interval, adj)
    if not data:
        return {"ok": False, "error": "upstream error"}
    df = _df_from_ohlc(data)
    if len(df) == 0:
        return {"ok": False, "error": "no data"}
    out = compute_indicators(df)
    meta = {"symbol": symbol, "range": range, "interval": interval}
    return {"ok": True, "meta": meta, "ohlc": df[["Open","High","Low","Close"]].reset_index().to_dict(orient="records"), "indicators": out.reset_index().to_dict(orient="records")}

@app.post("/v1/compute")
def v1_compute(body: dict = Body(...)):
    df = _df_from_ohlc(body.get("ohlc", []))
    if len(df) == 0:
        return {"ok": False, "error": "empty"}
    out = compute_indicators(df)
    return {"ok": True, "indicators": out.reset_index().to_dict(orient="records")}
