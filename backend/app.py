import os
import pandas as pd
import numpy as np
import requests
import yfinance as yf
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from .indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("ALLOWED_ORIGINS","*").split(","), allow_methods=["*"], allow_headers=["*"])

def _df_from_yf(symbol:str, period:str="1y", interval:str="1d")->pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    if not isinstance(df, pd.DataFrame) or df.empty: return pd.DataFrame()
    df = df.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close","Volume":"Volume"})
    df = df[["Open","High","Low","Close","Volume"]]
    df.index = pd.to_datetime(df.index)
    return df

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
def bundle(symbol:str, range:str="1y", interval:str="1d"):
    df = _df_from_yf(symbol, range, interval)
    if df.empty: return {"ok": False, "error": "no data"}
    meta = {"symbol": symbol, "range": range, "interval": interval}
    ohlc = df.reset_index().rename(columns={"index":"Date","Datetime":"Date"})
    ohlc["Date"] = pd.to_datetime(ohlc["Date"]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"ok": True, "meta": meta, "ohlc": ohlc.to_dict(orient="records")}

@app.post("/v1/compute")
def v1_compute(body:dict=Body(...)):
    if isinstance(body, dict) and "ohlc" in body:
        df = pd.DataFrame(body["ohlc"])
        df = df.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close","Volume":"Volume"})
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
    else:
        symbol = body.get("symbol","AAPL") if isinstance(body, dict) else "AAPL"
        rng = body.get("range","1y") if isinstance(body, dict) else "1y"
        interval = body.get("interval","1d") if isinstance(body, dict) else "1d"
        df = _df_from_yf(symbol, rng, interval)
    if df is None or df.empty: return {"ok": False, "error": "empty"}
    ind = compute_indicators(df.dropna().copy())
    out = {k: v.reset_index(drop=True).astype(float).round(6).tolist() for k, v in ind.items()}
    return {"ok": True, "indicators": out}
