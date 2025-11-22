import os, time, requests, pandas as pd
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from indicators import compute_indicators

API_BASE = os.getenv("DATA_API_BASE", "").rstrip("/")
API_KEY = os.getenv("DATA_API_KEY", "")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("ALLOWED_ORIGINS","*").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_CACHE = {}

def _df_from_ohlc(data):
    df = pd.DataFrame(data)
    if "t" in df.columns:
        df["t"] = pd.to_datetime(df["t"], unit="s", utc=True).dt.tz_localize(None)
        df = df.rename(columns={"t":"Date","o":"Open","h":"High","l":"Low","c":"Close","v":"Volume"})
        df = df.set_index("Date").sort_index()
    return df

def _fetch(symbol, range_):
    key = (symbol, range_)
    hit = _CACHE.get(key)
    if hit and time.time() - hit["t"] < 240:
        return hit["data"], True
    url = f"{API_BASE}/v1/ohlc?symbol={symbol}&range={range_}"
    headers = {"Accept":"application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    r = requests.get(url, headers=headers, timeout=30)
    j = r.json()
    if j.get("ok"):
        _CACHE[key] = {"t": time.time(), "data": j.get("data")}
        return j.get("data"), False
    return None, False

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
def bundle(symbol: str, range: str = "1Y", interval: str = "1d", adjusted: bool = True, currency: str = "USD"):
    if not API_BASE:
        return {"ok": False, "error": "DATA_API_BASE missing"}
    data, _ = _fetch(symbol, range)
    if not data:
        return {"ok": False, "error": "upstream error"}
    df = _df_from_ohlc(data)
    if len(df) == 0:
        return {"ok": False, "error": "no data"}
    df = df.dropna().copy()
    out = compute_indicators(df)
    meta = {"symbol": symbol, "range": range, "interval": interval, "adjusted": adjusted, "currency": currency, "rows": int(len(out))}
    return {"ok": True, "meta": meta, "ohlc": df[["Open","High","Low","Close","Volume"]].reset_index().to_dict(orient="records"), "indicators": out[["EMA9","EMA21","EMA50","EMA100","EMA200","BB_basis","BB_upper","BB_lower","ATR20","KC_basis","KC_upper","KC_lower","RSI","MACD","MACD_sig","MACD_hist","%K","%D","ST_RSI_K","ST_RSI_D","PSAR"]].reset_index().to_dict(orient="records")}

@app.post("/v1/compute")
def v1_compute(body: dict = Body(...)):
    df = _df_from_ohlc(body.get("ohlc", []))
    if len(df) == 0:
        return {"ok": False, "error": "empty"}
    out = compute_indicators(df)
    return {"ok": True, "indicators": out.reset_index().to_dict(orient="records")}
