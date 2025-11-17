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
from fastapi import APIRouter, Query
router = APIRouter()
import os, time, math, json, requests
def _now(): return int(time.time())
_CACHE={} ; _TTL=600
def _eod_symbol(s):
    if "." in s: return s
    return f"{s}.US"
def _fetch_ohlcv(symbol):
    key=os.environ.get("EODHD_API_KEY","")
    sym=_eod_symbol(symbol)
    url=f"https://eodhd.com/api/eod/{sym}?api_token={key}&from=2000-01-01&fmt=json"
    r=requests.get(url,timeout=30)
    if r.status_code!=200: return None
    arr=r.json()
    if not isinstance(arr,list) or not arr: return None
    arr=sorted(arr,key=lambda x:x["date"])
    t=[x["date"] for x in arr]
    o=[float(x["open"]) for x in arr]
    h=[float(x["high"]) for x in arr]
    l=[float(x["low"]) for x in arr]
    c=[float(x["close"]) for x in arr]
    v=[float(x.get("volume",0.0)) for x in arr]
    return {"time":t,"open":o,"high":h,"low":l,"close":c,"volume":v}
def _ema(vals,span):
    k=2/(span+1)
    ema=[]
    prev=None
    for x in vals:
        prev = x if prev is None else (x-prev)*k+prev
        ema.append(prev)
    return ema
def _rsi(close,period=14):
    gains=[];losses=[]
    for i in range(1,len(close)):
        d=close[i]-close[i-1]
        gains.append(max(d,0.0));losses.append(max(-d,0.0))
    if len(gains)<period: return [None]*len(close)
    avg_gain=sum(gains[:period])/period
    avg_loss=sum(losses[:period])/period
    rsi=[None]*(period)
    for i in range(period,len(close)-1):
        g=gains[i-1];l=losses[i-1]
        avg_gain=(avg_gain*(period-1)+g)/period
        avg_loss=(avg_loss*(period-1)+l)/period
        rs=math.inf if avg_loss==0 else avg_gain/avg_loss
        rsi.append(100-100/(1+rs))
    rsi.append(rsi[-1])
    return rsi
def _rolling_max(arr,win,i):
    a=max(arr[max(0,i-win+1):i+1])
    return a
def _rolling_min(arr,win,i):
    a=min(arr[max(0,i-win+1):i+1])
    return a
def _stoch(close,high,low,period=14,signal=3):
    k=[]
    for i in range(len(close)):
        if i<period-1: k.append(None); continue
        hh=max(high[i-period+1:i+1]); ll=min(low[i-period+1:i+1])
        val=None if hh==ll else (close[i]-ll)/(hh-ll)*100
        k.append(val)
    d=[]
    for i in range(len(k)):
        if i<period-1+signal-1: d.append(None); continue
        vals=[x for x in k[i-signal+1:i+1] if x is not None]
        d.append(None if len(vals)<signal else sum(vals)/signal)
    return k,d
def _macd(close,fast=12,slow=26,signal=9):
    ema_fast=_ema(close,fast)
    ema_slow=_ema(close,slow)
    macd=[ema_fast[i]-ema_slow[i] for i in range(len(close))]
    sig=_ema(macd,signal)
    hist=[macd[i]-sig[i] for i in range(len(close))]
    return macd,sig,hist
def _pivots(high,low,win=5,cap=12):
    piv=[]
    for i in range(len(high)):
        if i<win or i>=len(high)-win: continue
        is_h=high[i]==max(high[i-win:i+win+1])
        is_l=low[i]==min(low[i-win:i+win+1])
        if is_h: piv.append({"i":i,"type":"H","p":high[i]})
        elif is_l: piv.append({"i":i,"type":"L","p":low[i]})
    return piv[-cap:]
def _trendlines(piv):
    highs=[x for x in piv if x["type"]=="H"]
    lows=[x for x in piv if x["type"]=="L"]
    lines=[]
    if len(highs)>=2:
        a=highs[-2];b=highs[-1]
        lines.append({"from":{"i":a["i"],"p":a["p"]},"to":{"i":b["i"],"p":b["p"]},"kind":"H"})
    if len(lows)>=2:
        a=lows[-2];b=lows[-1]
        lines.append({"from":{"i":a["i"],"p":a["p"]},"to":{"i":b["i"],"p":b["p"]},"kind":"L"})
    return lines
@router.get("/v1/bundle")
def bundle(symbol: str = Query(...)):
    key=(symbol.upper(),)
    now=_now()
    hit=_CACHE.get(key)
    if hit and now-hit["ts"]<_TTL:
        d=hit["data"].copy(); d["cache"]["stale"]=False; return d
    ohlcv=_fetch_ohlcv(symbol)
    if not ohlcv:
        if hit:
            d=hit["data"].copy(); d["cache"]["stale"]=True; return d
        return {"meta":{"symbol":symbol},"ohlcv":{"time":[],"open":[],"high":[],"low":[],"close":[],"volume":[]},"indicators":{"ema20":None,"ema50":None,"rsi14":None,"stochK":None,"stochD":None,"macdLine":None,"macdSignal":None,"macdHist":None,"last":None},"trend":{"pivots":[],"lines":[]},"cache":{"ttl_sec":_TTL,"source":"EODHD","stale":False}}
    t=ohlcv["time"]; c=ohlcv["close"]; h=ohlcv["high"]; l=ohlcv["low"]
    ema20=_ema(c,20); ema50=_ema(c,50)
    rsi14=_rsi(c,14)
    stK,stD=_stoch(c,h,l,14,3)
    mL,mS,mH=_macd(c,12,26,9)
    piv=_pivots(h,l,5,12); lines=_trendlines(piv)
    data={"meta":{"symbol":symbol,"currency":"USD","tz":"UTC","asof":t[-1] if t else None},"ohlcv":ohlcv,"indicators":{"ema20":ema20,"ema50":ema50,"rsi14":rsi14,"stochK":stK,"stochD":stD,"macdLine":mL,"macdSignal":mS,"macdHist":mH,"last":c[-1] if c else None},"trend":{"pivots":piv,"lines":lines},"cache":{"ttl_sec":_TTL,"source":"EODHD","stale":False}}
    _CACHE[key]={"ts":now,"data":data}
    return data
try:
    app.include_router(router)
except:
    pass
