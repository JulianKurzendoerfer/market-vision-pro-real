import os, time
from datetime import date, timedelta, timezone, datetime
from typing import Dict, Any, List
import requests, pandas as pd, numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

EOD_TOKEN = os.getenv("EODHD_API_KEY", "").strip()
if not EOD_TOKEN:
    raise RuntimeError("EODHD_API_KEY not configured")

class TTLCache:
    def __init__(self, ttl_sec:int=900):
        self.ttl = ttl_sec
        self._store: Dict[str, Any] = {}
    def get(self, k:str):
        v = self._store.get(k)
        if not v: return None
        exp, data = v
        if time.time() > exp:
            self._store.pop(k, None); return None
        return data
    def set(self, k:str, data:Any):
        self._store[k] = (time.time()+self.ttl, data)

cache = TTLCache(ttl_sec=int(os.getenv("EOD_CACHE_SECONDS","900")))

def ema(s: pd.Series, n:int) -> pd.Series: return s.ewm(span=n, adjust=False).mean()
def rsi14(close: pd.Series, n=14) -> float:
    d = close.diff()
    up = pd.Series(np.where(d>0, d, 0.0), index=close.index).rolling(n).mean()
    dn = pd.Series(np.where(d<0, -d, 0.0), index=close.index).rolling(n).mean()
    rs = up/(dn+1e-12); rsi = 100 - 100/(1+rs)
    return float(rsi.iloc[-1])
def stoch_kd(h:pd.Series, l:pd.Series, c:pd.Series, n=14, ksm=3, dsm=3)->tuple[float,float]:
    ll=l.rolling(n).min(); hh=h.rolling(n).max()
    k=100*(c-ll)/(hh-ll+1e-12); ksmv=k.rolling(ksm).mean(); d=ksmv.rolling(dsm).mean()
    return float(ksmv.iloc[-1]), float(d.iloc[-1])
def macd_ln_sig(c:pd.Series, fast=12, slow=26, signal=9)->tuple[float,float]:
    ln = ema(c, fast)-ema(c, slow); sig = ema(ln, signal)
    return float(ln.iloc[-1]), float(sig.iloc[-1])

def eod_search(query:str)->List[Dict[str,Any]]:
    url=f"https://eodhd.com/api/search/{requests.utils.quote(query)}"
    r=requests.get(url, params={"api_token":EOD_TOKEN,"fmt":"json"}, timeout=12)
    if r.status_code!=200: raise HTTPException(r.status_code, r.text)
    items=r.json() or []
    out=[]
    for it in items[:10]:
        out.append({
            "code": it.get("Code") or it.get("code"),
            "name": it.get("Name") or it.get("name"),
            "exchange": it.get("Exchange") or it.get("exchange"),
            "score": it.get("Score") or it.get("score"),
        })
    return out

def eod_ohlcv(symbol:str, days:int=300)->pd.DataFrame:
    key=f"eod:{symbol.lower()}"
    cdf=cache.get(key)
    if cdf is not None: return cdf.copy()
    to=date.today(); frm=to - timedelta(days=int(days*1.4))
    url=f"https://eodhd.com/api/eod/{symbol}"
    r=requests.get(url, params={"api_token":EOD_TOKEN,"from":frm.isoformat(),"to":to.isoformat(),"fmt":"json"}, timeout=15)
    if r.status_code==402 or r.status_code==429: raise HTTPException(r.status_code, "EODHD limit reached")
    if r.status_code!=200: raise HTTPException(r.status_code, r.text)
    js=r.json() or []
    if not js: raise HTTPException(404, "No EOD data")
    df=pd.DataFrame(js)
    if "adjusted_close" not in df and "adj_close" in df: df=df.rename(columns={"adj_close":"adjusted_close"})
    df["date"]=pd.to_datetime(df["date"])
    df=df.sort_values("date").reset_index(drop=True)
    cache.set(key, df)
    return df.copy()

def payload_bars(df:pd.DataFrame, symbol:str)->Dict[str,Any]:
    last=float(df["close"].iloc[-1])
    bars=[]
    for _,r in df.tail(200).iterrows():
        bars.append({
            "date": r["date"].date().isoformat(),
            "open": float(r["open"]), "high": float(r["high"]),
            "low": float(r["low"]), "close": float(r["close"]),
            "adjusted_close": float(r.get("adjusted_close", r["close"])),
            "volume": float(r.get("volume", 0.0)),
        })
    return {"symbol":symbol, "last":{"price":round(last,2),"currency":"USD"}, "bars":bars}

def payload_indicators(df:pd.DataFrame, symbol:str)->Dict[str,Any]:
    c=df["close"]; h=df["high"]; l=df["low"]
    k,d = stoch_kd(h,l,c)
    ln,sig = macd_ln_sig(c)
    return {
        "symbol":symbol,
        "price": float(c.iloc[-1]),
        "rsi": rsi14(c,14),
        "stoch": {"k": k, "d": d},
        "macd": {"line": ln, "signal": sig},
        "ema": {"e20": float(ema(c,20).iloc[-1]), "e50": float(ema(c,50).iloc[-1])}
    }

app=FastAPI()
origins=[o.strip() for o in os.getenv("ALLOWED_ORIGINS","*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health(): return {"ok":True,"asof":datetime.now(timezone.utc).isoformat()}

@app.get("/v1/resolve")
def resolve(q: str = Query(..., min_length=1)):
    return eod_search(q)

@app.get("/v1/ohlcv")
def ohlcv(symbol: str = Query(..., min_length=1)):
    df=eod_ohlcv(symbol)
    return payload_bars(df, symbol)

@app.get("/v1/indicators")
def indicators(symbol: str = Query(..., min_length=1)):
    df=eod_ohlcv(symbol)
    return payload_indicators(df, symbol)
