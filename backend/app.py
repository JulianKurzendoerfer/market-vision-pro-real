from pydantic import BaseModel

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from indicators import compute

API=os.getenv("EODHD_API_KEY","")
ORIG=os.getenv("ALLOWED_ORIGINS","*")
APP=FastAPI()
app=APP
app.add_middleware(CORSMiddleware, allow_origins=[ORIG,"*"], allow_methods=["*"], allow_headers=["*"])

_CACHE={}

def _rng_to_from(r):
    now=dt.date.today()
    if r=="1M": return now-dt.timedelta(days=31)
    if r=="3M": return now-dt.timedelta(days=93)
    if r=="6M": return now-dt.timedelta(days=186)
    if r=="1Y": return now-dt.timedelta(days=372)
    if r=="5Y": return now-dt.timedelta(days=1860)
    return now-dt.timedelta(days=3650)

def _fetch(symbol, r):
    key=(symbol,r)
    hit=_CACHE.get(key)
    if hit and time.time()-hit["t"]<240:
        return hit["data"], True
    start=_rng_to_from(r).strftime("%Y-%m-%d")
    url=f"https://eodhd.com/api/eod/{symbol}?from={start}&period=d&order=a&fmt=json&api_token={API}"
    j=requests.get(url,timeout=20).json()
    df=pd.DataFrame(j)
    if "date" not in df.columns: df=pd.DataFrame(columns=["date","open","high","low","close","volume"])
    df=df.rename(columns=str.lower)
    df=df.sort_values("date")
    _CACHE[key]={"t":time.time(),"data":df}
    return df, False

@app.get("/health")
def health():
    return {"ok":True,"asof":dt.datetime.utcnow().isoformat()}

@app.get("/v1/bundle")
def bundle(symbol: str=Query(...), range: str=Query("1Y")):
    df,stale=_fetch(symbol.upper(), range)
    ind=compute(df) if len(df)>0 else {k:[] for k in ["rsi","stochK","stochD","macdLine","macdSignal","macdHist","ema20","ema50","th","tl"]}
    out={
        "ok":True,
        "asof":dt.datetime.utcnow().isoformat(),
        "meta":{"symbol":symbol.upper(),"currency":"USD","tz":"UTC"},
        "ohlcv":{
            "time":df["date"].astype(str).tolist() if len(df) else [],
            "open":df.get("open",pd.Series(dtype=float)).tolist() if len(df) else [],
            "high":df.get("high",pd.Series(dtype=float)).tolist() if len(df) else [],
            "low":df.get("low",pd.Series(dtype=float)).tolist() if len(df) else [],
            "close":df.get("close",pd.Series(dtype=float)).tolist() if len(df) else [],
            "volume":df.get("volume",pd.Series(dtype=float)).tolist() if len(df) else [],
        },
        "indicators":ind,
        "cache":{"stale":stale,"ttl":240},
        "available":True
    }
    return out

@app.get("/v1/resolve")
def resolve(q: str=Query(...), prefer: str=Query("US")):
    return {"ok":True,"asof":dt.datetime.utcnow().isoformat(),"hits":[{"code":q.upper(),"score":1}]}

class OhlcvIn(BaseModel):
    t:list|None=None
    h:list|None=None
    l:list|None=None
    c:list|None=None
    v:list|None=None

@app.post("/v1/compute")
def v1_compute(body: OhlcvIn):
    o={"t":body.t or [],"h":body.h or [],"l":body.l or [],"c":body.c or [],"v":body.v or []}
    ind=compute_from_ohlcv(o)
    return {"ok":True,"indicators":ind,"options":{"supported":False}}

@app.get("/v1/compute_bundle")
def v1_compute_bundle(symbol: str, range: str="1Y"):
    b=bundle(symbol=symbol, range=range)
    o=b.get("ohlcv") if isinstance(b,dict) else None
    ind=compute_from_ohlcv(o) if o else {}
    r={"ok":True,"meta":b.get("meta") if isinstance(b,dict) else {}, "ohlcv":o or {}, "indicators":ind, "options":{"supported":False}}
    return r
