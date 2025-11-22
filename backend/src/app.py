from fastapi import FastAPI, Query, Body
from pydantic import BaseModel
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import yfinance as yf
from backend.src.indicators import compute_indicators

app = FastAPI()

class OhlcIn(BaseModel):
    t: list[int]
    o: list[float]
    h: list[float]
    l: list[float]
    c: list[float]
    v: list[float] | None = None

def _df_from_ohlc(obj: OhlcIn) -> pd.DataFrame:
    idx = pd.to_datetime(pd.Series(obj.t, dtype="int64"), unit="ms", utc=True).tz_convert(None)
    df = pd.DataFrame({"Open":obj.o,"High":obj.h,"Low":obj.l,"Close":obj.c}, index=idx)
    if obj.v is not None: df["Volume"] = obj.v
    return df.dropna()

def _bundle(df: pd.DataFrame, meta: dict):
    idx = (pd.to_datetime(df.index).tz_localize("UTC") if df.index.tz is None else df.index).astype("int64")//10**6
    out = {
        "ok": True,
        "meta": meta,
        "t": idx.tolist(),
        "o": df["Open"].astype(float).round(6).tolist(),
        "h": df["High"].astype(float).round(6).tolist(),
        "l": df["Low"].astype(float).round(6).tolist(),
        "c": df["Close"].astype(float).round(6).tolist(),
    }
    if "Volume" in df.columns:
        out["v"] = df["Volume"].fillna(0).astype(float).round(6).tolist()
    return out

@app.get("/health")
def health():
    return {"ok": True, "asof": datetime.now(timezone.utc).isoformat()}

def _period_for_range(rng: str):
    s = (rng or "1Y").upper()
    m = {"1D":"1d","5D":"5d","1W":"7d","1MO":"1mo","3MO":"3mo","6MO":"6mo","1Y":"1y","2Y":"2y","5Y":"5y","10Y":"10y","YTD":"ytd","MAX":"max"}
    return m.get(s, "1y")

def _interval_for_period(period: str):
    return "1h" if period in ("1d","5d","7d") else "1d"

@app.get("/v1/bundle")
def v1_bundle(symbol: str = Query(...), range: str = Query("1Y"), adjusted: bool = True):
    period = _period_for_range(range)
    interval = _interval_for_period(period)
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=adjusted, progress=False)
    if df is None or len(df)==0:
        return {"ok": False, "error": "no_data"}
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.dropna()
    meta = {"symbol": symbol.upper(), "period": period, "interval": interval, "rows": len(df)}
    ind = compute_indicators(df)
    ind_cols = [c for c in ind.columns if c not in ("Open","High","Low","Close","Volume")]
    meta["indicators"] = ind_cols
    return _bundle(ind, meta)

@app.post("/v1/compute")
def v1_compute(body: OhlcIn = Body(...)):
    df = _df_from_ohlc(body)
    if df.empty:
        return {"ok": False, "error": "empty"}
    ind = compute_indicators(df)
    return _bundle(ind, {"rows": len(ind), "source": "client"})
