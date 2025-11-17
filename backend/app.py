import os, json, time, datetime as dt, requests, pandas as pd, numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

APP=FastAPI()
app=APP
orig=os.environ.get("ALLOWED_ORIGINS","*").split(",")
APP.add_middleware(CORSMiddleware,allow_origins=[o.strip() for o in orig if o.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

TOK=os.environ.get("EODHD_API_KEY","")
BASE="https://eodhd.com/api"
CACHE={}
TTL=300

def _get(url,params):
    params=dict(params); params["api_token"]=TOK; params["fmt"]="json"
    r=requests.get(url,params=params,timeout=20)
    if r.status_code==402 or r.status_code==429: raise HTTPException(status_code=r.status_code, detail="EODHD limit")
    if r.status_code>=400: raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()

def _cache(key,fn):
    now=time.time()
    v=CACHE.get(key)
    if v and now-v[0]<TTL: return v[1]
    data=fn()
    CACHE[key]=(now,data)
    return data

@APP.get("/health")
def health():
    return {"ok":True,"asof":dt.datetime.utcnow().isoformat()}

@APP.get("/v1/resolve")
def resolve(q:str, prefer:str="US"):
    key=("resolve",q,prefer)
    def run():
        x=_get(f"{BASE}/search/{q}",{"limit":10})
        if isinstance(x,dict) and "data" in x: x=x["data"]
        res=[]
        seen=set()
        for it in x:
            code=it.get("Code") or it.get("code") or it.get("symbol") or it.get("Symbol") or ""
            exch=it.get("Exchange") or it.get("exchange") or it.get("Exch") or ""
            name=it.get("Name") or it.get("name") or ""
            if not code: continue
            k=(code,exch)
            if k in seen: continue
            seen.add(k)
            res.append({"code":code,"exchange":exch,"name":name,"score":2 if exch==prefer else 1})
        res.sort(key=lambda a:(-a["score"],a["code"]))
        return res[:5]
    return _cache(key,run)

def _eod(symbol):
    today=dt.date.today().isoformat()
    frm=(dt.date.today()-dt.timedelta(days=550)).isoformat()
    def try_one(sym):
        return _get(f"{BASE}/eod/{sym}",{"from":frm,"to":today,"order":"a","period":"d"})
    try:
        d=try_one(symbol)
    except HTTPException:
        d=[]
    if not d:
        try:
            d=try_one(f"{symbol}.US")
        except HTTPException:
            d=[]
    if not isinstance(d,list) or not d: raise HTTPException(status_code=404,detail="No data")
    return d

@APP.get("/v1/ohlcv")
def ohlcv(symbol:str):
    key=("ohlcv",symbol)
    def run():
        d=_eod(symbol)
        return d
    return _cache(key,run)

def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean()

@APP.get("/v1/indicators")
def indicators(symbol:str):
    key=("ind",symbol)
    def run():
        d=_eod(symbol)
        df=pd.DataFrame(d)
        for c in ["open","high","low","close","adjusted_close"]:
            if c in df.columns: pass
        c=df.get("adjusted_close",df["close"]).astype(float).values
        h=df["high"].astype(float).values
        l=df["low"].astype(float).values
        price=float(c[-1])
        n=14
        delta=np.diff(c, prepend=c[0])
        gain=np.where(delta>0,delta,0.0)
        loss=np.where(delta<0,-delta,0.0)
        roll_up=pd.Series(gain).rolling(n).mean()
        roll_down=pd.Series(loss).rolling(n).mean()
        rs=roll_up/roll_down
        rsi=100-(100/(1+rs))
        rsi=float(rsi.iloc[-1])
        hh=pd.Series(h).rolling(n).max()
        ll=pd.Series(l).rolling(n).min()
        k=100*(pd.Series(c)-ll)/(hh-ll)
        dline=k.rolling(3).mean()
        stoch_k=float(k.iloc[-1])
        stoch_d=float(dline.iloc[-1])
        ema20=float(_ema(c,20).iloc[-1])
        ema50=float(_ema(c,50).iloc[-1])
        ema12=_ema(c,12)
        ema26=_ema(c,26)
        macd_line=float((ema12-ema26).iloc[-1])
        macd_signal=float(pd.Series(ema12-ema26).ewm(span=9,adjust=False).mean().iloc[-1])
        return {"price":price,"rsi":rsi,"stoch_k":stoch_k,"stoch_d":stoch_d,"macd_line":macd_line,"macd_signal":macd_signal,"ema20":ema20,"ema50":ema50}
    return _cache(key,run)

# redeploy 2025-11-17 14:12:19
