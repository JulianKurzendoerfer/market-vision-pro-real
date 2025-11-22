import os, json, math, datetime as dt
import pandas as pd
import numpy as np
import requests
from fastapi import FastAPI, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from backend.indicators import compute_indicators

API_BASE = os.environ.get("DATA_API_BASE", "https://eodhd.com/api")
API_KEY = os.environ.get("DATA_API_KEY", "")

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def _clean(v):
    if isinstance(v, (pd.Series, np.ndarray, list)):
        arr = pd.Series(v).astype(float).replace([np.inf, -np.inf], np.nan).tolist()
        return [None if (not isinstance(x,(int,float)) or not math.isfinite(x)) else float(x) for x in arr]
    if v is None: return None
    try:
        x = float(v)
        return None if not math.isfinite(x) else x
    except: return None

def _to_df(payload):
    t = payload.get("t", [])
    o = payload.get("o", [])
    h = payload.get("h", [])
    l = payload.get("l", [])
    c = payload.get("c", [])
    v = payload.get("v", [])
    if not (len(t)==len(o)==len(h)==len(l)==len(c)>0): return None
    idx = pd.to_datetime(t)
    df = pd.DataFrame({"Open":o,"High":h,"Low":l,"Close":c,"Volume":v if len(v)==len(c) else [None]*len(c)}, index=idx).dropna()
    return df

def _bundle(df, tp):
    ind, trend = df, tp
    out = {
        "t": [x.isoformat() for x in ind.index.to_pydatetime()],
        "o": _clean(ind["Open"]), "h": _clean(ind["High"]), "l": _clean(ind["Low"]), "c": _clean(ind["Close"]), "v": _clean(ind.get("Volume", [])),
        "ind": {
            "ema9": _clean(ind["EMA9"]), "ema21": _clean(ind["EMA21"]), "ema50": _clean(ind["EMA50"]), "ema100": _clean(ind["EMA100"]), "ema200": _clean(ind["EMA200"]),
            "bb_mid": _clean(ind["BB_mid"]), "bb_upper": _clean(ind["BB_upper"]), "bb_lower": _clean(ind["BB_lower"]),
            "atr20": _clean(ind["ATR20"]), "kc_upper": _clean(ind["KC_upper"]), "kc_lower": _clean(ind["KC_lower"]),
            "rsi14": _clean(ind["RSI14"]), "macd": _clean(ind["MACD"]), "macds": _clean(ind["MACDS"]), "macdh": _clean(ind["MACDH"]),
            "stochK": _clean(ind["STOCHK"]), "stochD": _clean(ind["STOCHD"]), "psar": _clean(ind["PSAR"]),
            "trend_low_idx": list(map(int, trend["lows"])) if trend["lows"].size else [],
            "trend_high_idx": list(map(int, trend["highs"])) if trend["highs"].size else [],
            "trend_levels": _clean(trend["levels"]), "trend_counts": _clean(trend["counts"]), "trend_strength": _clean(trend["strength"]),
            "close": _clean(ind["Close"]),
        }
    }
    return {"ok": True, "data": out}

def _eodhd_download(symbol, interval, years):
    end = pd.Timestamp.utcnow().normalize()
    start = end - pd.DateOffset(years=int(years))
    if interval == "1h":
        url = f"{API_BASE}/intraday/{symbol}"
        params = {"from": start.strftime("%Y-%m-%d"), "to": end.strftime("%Y-%m-%d"), "interval": "60m", "api_token": API_KEY, "fmt": "json"}
    elif interval == "1wk":
        url = f"{API_BASE}/eod/{symbol}"
        params = {"from": start.strftime("%Y-%m-%d"), "to": end.strftime("%Y-%m-%d"), "period": "w", "api_token": API_KEY, "fmt": "json"}
    else:
        url = f"{API_BASE}/eod/{symbol}"
        params = {"from": start.strftime("%Y-%m-%d"), "to": end.strftime("%Y-%m-%d"), "period": "d", "api_token": API_KEY, "fmt": "json"}
    r = requests.get(url, params=params, timeout=20)
    if r.status_code != 200: return None, f"http {r.status_code}"
    js = r.json()
    if not isinstance(js, list) or not js: return None, "empty"
    recs = []
    for row in js:
        t = row.get("date") or row.get("datetime") or row.get("timestamp")
        if isinstance(t, (int,float)): ts = pd.to_datetime(int(t), unit="s")
        else: ts = pd.to_datetime(str(t))
        recs.append([ts, float(row.get("open", np.nan)), float(row.get("high", np.nan)), float(row.get("low", np.nan)), float(row.get("close", np.nan)), float(row.get("volume", 0))])
    df = pd.DataFrame(recs, columns=["time","Open","High","Low","Close","Volume"]).dropna()
    df = df.set_index("time").sort_index()
    if interval=="1h":
        now = pd.Timestamp.utcnow().tz_localize(None)
        step = pd.Timedelta(hours=1)
        if len(df) and (now - df.index[-1].to_pydatetime()) < step: df = df.iloc[:-1]
    return df, None

@app.get("/health")
def health():
    return {"ok": True, "asof": pd.Timestamp.utcnow().isoformat()}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), years: int = Query(1, ge=1, le=10), interval: str = Query("1d")):
    df, err = _eodhd_download(symbol.strip(), interval.strip(), years)
    if df is None: return {"ok": False, "error": err or "fetch_failed"}
    ind, tp = compute_indicators(df)
    return _bundle(ind, tp)

@app.post("/v1/compute")
def v1_compute(body: dict = Body(...)):
    df = _to_df(body)
    if df is None or df.empty: return {"ok": False, "error": "bad_input"}
    ind, tp = compute_indicators(df)
    return _bundle(ind, tp)
