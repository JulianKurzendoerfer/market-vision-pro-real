import os, json
from datetime import datetime, timezone
import numpy as np, pandas as pd, requests, yfinance as yf
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app=FastAPI()
origins=os.environ.get("ALLOWED_ORIGINS","*").split(",")
app.add_middleware(CORSMiddleware,allow_origins=[o.strip() for o in origins if o.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.get("/health")
def health(): return {"ok":True,"asof":datetime.now(timezone.utc).isoformat()}

def _ohlc(symbol,period="6mo",interval="1d"):
    df=yf.Ticker(symbol).history(period=period,interval=interval,auto_adjust=False)
    if df is None or df.empty: raise HTTPException(404,detail="No data")
    df=df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    df.index=df.index.tz_localize(None)
    return df

@app.get("/v1/ohlcv")
def ohlcv(symbol: str=Query(...,min_length=1)):
    df=_ohlc(symbol)
    last=float(df["close"].iloc[-1])
    return {"symbol":symbol.upper(),"last":last,"asof":df.index[-1].isoformat()}

def _ema(s,span): return s.ewm(span=span,adjust=False).mean()
def _rsi(s,period=14):
    d=s.diff()
    up=d.clip(lower=0).rolling(period).mean()
    dn=(-d.clip(upper=0)).rolling(period).mean()
    rs=up/dn
    return 100-100/(1+rs)
def _stoch_k(h,l,c,period=14):
    hh=h.rolling(period).max()
    ll=l.rolling(period).min()
    return 100*(c-ll)/(hh-ll)
def _macd(s,fast=12,slow=26,signal=9):
    macd=_ema(s,fast)-_ema(s,slow)
    sig=_ema(macd,signal)
    return macd,sig

@app.get("/v1/indicators")
def indicators(symbol: str=Query(...,min_length=1)):
    df=_ohlc(symbol,period="12mo",interval="1d")
    close=df["close"]
    rsi=_rsi(close).iloc[-1]
    k=_stoch_k(df["high"],df["low"],close).iloc[-1]
    e20=_ema(close,20).iloc[-1]
    e50=_ema(close,50).iloc[-1]
    macd,signal=_macd(close)
    return {
        "symbol":symbol.upper(),
        "rsi":float(np.round(rsi,2)),
        "stoch_k":float(np.round(k,2)),
        "ema20":float(np.round(e20,2)),
        "ema50":float(np.round(e50,2)),
        "macd_line":float(np.round(macd.iloc[-1],2)),
        "macd_signal":float(np.round(signal.iloc[-1],2))
    }

@app.get("/v1/resolve")
def resolve(q: str=Query(...,min_length=1), prefer: str="US"):
    tok=os.environ.get("EODHD_API_KEY","").strip()
    if tok:
        url=f"https://eodhd.com/api/search/{q}?api_token={tok}&fmt=json"
        r=requests.get(url,timeout=12)
        if r.ok:
            data=r.json()
            out=[]
            for x in data:
                code=x.get("Code") or x.get("code") or ""
                exch=x.get("Exchange") or x.get("exchange") or ""
                name=x.get("Name") or x.get("name") or ""
                if code: out.append({"code":code,"exchange":exch,"name":name,"score":1})
            if prefer:
                out=sorted(out,key=lambda x:(x["exchange"]!=prefer,len(x["code"])))
            return out[:10]
    return [{"code":"AAPL","exchange":"US","name":"Apple Inc."},{"code":"APC","exchange":"F","name":"Apple Inc."}]
