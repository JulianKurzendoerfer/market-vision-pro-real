import os
from datetime import datetime, timezone
import requests, pandas as pd, numpy as np, yfinance as yf
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()
orig=os.environ.get("ALLOWED_ORIGINS","*").split(",")
app.add_middleware(CORSMiddleware,allow_origins=[o.strip() for o in orig if o.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.get("/health")
def health():
    return {"ok":True,"asof":datetime.now(timezone.utc).isoformat()}

EOD=os.environ.get("EODHD_API_KEY","")

@app.get("/v1/resolve")
def resolve(q: str, prefer: str="US"):
    if not EOD: raise HTTPException(500,"no_api_key")
    u=f"https://eodhd.com/api/search-ticker/?search={q}&api_token={EOD}&fmt=json"
    r=requests.get(u,timeout=15); r.raise_for_status()
    data=r.json()
    for d in data:
        d["score"]=1
        if d.get("exchangeShortName")==prefer: d["score"]=2
        if d.get("Code","").upper()==q.upper(): d["score"]=3
    data=sorted(data,key=lambda d:d.get("score",0),reverse=True)[:10]
    return data

def to_rows(df):
    out=[]
    for t,o,h,l,c,v in zip(df.index,df["Open"],df["High"],df["Low"],df["Close"],df["Volume"]):
        out.append({"t":datetime.fromtimestamp(int(t.timestamp()),tz=timezone.utc).isoformat(),"o":float(o),"h":float(h),"l":float(l),"c":float(c),"v":float(v)})
    return out

@app.get("/v1/ohlcv")
def ohlcv(symbol: str):
    try:
        df=yf.Ticker(symbol).history(period="1y",interval="1d",auto_adjust=False)
        if df.empty: raise HTTPException(404,"no_data")
        return {"rows":to_rows(df)}
    except Exception:
        raise HTTPException(502,"upstream_unavailable")
