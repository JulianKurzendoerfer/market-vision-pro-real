import os,json,math
from datetime import datetime,timezone
import requests,pandas as pd,numpy as np
from fastapi import FastAPI,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware

EOD=os.environ.get("EODHD_API_KEY","")
ALLOW=os.environ.get("ALLOWED_ORIGINS","*").split(",")
app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=[o.strip() for o in ALLOW if o.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def jget(path,params=None,timeout=8):
    if not EOD: raise HTTPException(500,"missing_token")
    p=dict(params or {}); p["api_token"]=EOD; p["fmt"]="json"
    r=requests.get("https://eodhd.com"+path,params=p,timeout=timeout)
    if r.status_code!=200: raise HTTPException(502,"upstream_http_error")
    try: return r.json()
    except: raise HTTPException(502,"upstream_json_error")

@app.get("/health")
def health(): return {"ok":True,"asof":datetime.now(timezone.utc).isoformat()}

@app.get("/v1/resolve")
def resolve(q:str=Query(...,min_length=1),limit:int=15,prefer:str="US"):
    data=jget(f"/api/search/{q}",{"limit":limit,"type":"stock"})
    out=[]
    for x in data:
        code=x.get("Code",""); exch=x.get("Exchange",""); name=x.get("Name","")
        score=2 if prefer.upper() in exch.upper() else 1
        out.append({"code":code,"exchange":exch,"name":name,"score":score})
    out.sort(key=lambda z:(-z["score"],z["code"]))
    return out

def intraday(symbol,interval):
    raw=jget(f"/api/intraday/{symbol}",{"interval":interval,"sort":"asc","limit":5000})
    if not isinstance(raw,list) or not raw: raise HTTPException(404,"no_bars")
    rows=[]
    for r in raw:
        t=r.get("timestamp") or r.get("datetime") or r.get("date")
        if isinstance(t,str):
            try: ts=int(datetime.fromisoformat(t.replace("Z","+00:00")).timestamp())
            except: continue
        else: ts=int(t)
        rows.append({"t":ts,"o":float(r["open"]),"h":float(r["high"]),"l":float(r["low"]),"c":float(r["close"]),"v":float(r.get("volume",0.0))})
    return rows

@app.get("/v1/ohlcv")
def ohlcv(symbol:str,interval:str="60m"):
    bars=intraday(symbol,interval)
    return {"symbol":symbol,"interval":interval,"bars":bars}

def ema(x,span): return x.ewm(span=span,adjust=False).mean()
def rsi(close,period=14):
    d=close.diff().fillna(0); up=d.clip(lower=0); dn=(-d).clip(lower=0)
    rs=ema(up,period)/ema(dn,period); return 100-(100/(1+rs))
def stoch(h,l,c,k=14,d=3,s=3):
    ll=l.rolling(k).min(); hh=h.rolling(k).max()
    kline=100*(c-ll)/(hh-ll).replace(0,np.nan); kline=kline.rolling(s).mean(); dline=kline.rolling(d).mean()
    return kline,dline
def macd(c,fa=12,sl=26,si=9):
    m=ema(c,fa)-ema(c,sl); s=ema(m,si); h=m-s; return m,s,h
def last(v):
    v=v.dropna()
    return None if v.empty else float(v.iloc[-1])

@app.get("/v1/indicators")
def indicators(symbol:str,interval:str="60m"):
    bars=intraday(symbol,interval)
    df=pd.DataFrame(bars); df["dt"]=pd.to_datetime(df["t"],unit="s",utc=True); df.set_index("dt",inplace=True)
    c=df["c"]; h=df["h"]; l=df["l"]
    e20=ema(c,20); e50=ema(c,50); r=rsi(c,14); k,d=stoch(h,l,c,14,3,3); m,s,hh=macd(c,12,26,9)
    return {"symbol":symbol,"interval":interval,"ema20":last(e20),"ema50":last(e50),"rsi14":last(r),"stochK":last(k),"stochD":last(d),"macd":last(m),"macdSignal":last(s),"macdHist":last(hh)}
