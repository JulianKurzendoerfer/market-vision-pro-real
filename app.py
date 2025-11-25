import os, time, datetime as dt, requests, pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from indicators import compute

API=os.getenv("EODHD_API_KEY","")
ORIG=os.getenv("ALLOWED_ORIGINS","*")

app=FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=[ORIG,"*"], allow_methods=["*"], allow_headers=["*"])

_CACHE={}
def _df_from_ohlc(data):
    try:
        rows=data["candles"]
        if not rows: return None
        df=pd.DataFrame(rows)
        if "t" in df.columns: df["date"]=pd.to_datetime(df["t"],unit="s").dt.tz_localize("UTC").dt.tz_convert("Europe/Berlin").dt.date
        for c in ["o","h","l","c","v"]:
            if c in df.columns: df[c]=pd.to_numeric(df[c],errors="coerce")
        df=df.rename(columns={"o":"Open","h":"High","l":"Low","c":"Close","v":"Volume"})
        df=df.dropna(subset=["Open","High","Low","Close"])
        return df
    except Exception:
        return None

@app.get("/health")
def health():
    return {"ok": True}

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
    start=_rng_to_from(r)
    url=f"https://eodhd.com/api/eod/{symbol}?period=d&order=a&from={start:%Y-%m-%d}&api_token={API}&fmt=json"
    try:
        j=requests.get(url,timeout=25).json()
        if isinstance(j, list):
            df=pd.DataFrame(j)
            if "date" in df.columns: df["date"]=pd.to_datetime(df["date"]).dt.date
            df=df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
            data={"candles":df.rename(columns={"date":"t","Open":"o","High":"h","Low":"l","Close":"c","Volume":"v"}).assign(t=lambda x: pd.to_datetime(x["t"]).astype("int64")//10**9).to_dict("records")}
        else:
            data=j
        _CACHE[key]={"t":time.time(),"data":data}
        return data, False
    except Exception:
        return None, False

@app.get("/v1/bundle")
def bundle(symbol: str, range: str="1Y", interval: str="1d", adjusted: bool=True):
    data,_=_fetch(symbol, range)
    if not data: return {"ok": False, "error": "upstream"}
    df=_df_from_ohlc(data)
    if df is None or len(df)==0: return {"ok": False, "error":"no data"}
    out=compute(df.copy())
    meta={"symbol":symbol,"range":range,"interval":interval}
    return {"ok": True,"meta":meta,"ohlc": df[["Open","High","Low","Close","Volume"]].round(6).to_dict(orient="list"),"indicators": out.reset_index().to_dict(orient="list")}

class Body(BaseModel):
    ohlc: list

@app.post("/v1/compute")
def v1_compute(body: Body):
    df=pd.DataFrame(body.ohlc, columns=["Open","High","Low","Close","Volume"])
    if len(df)==0: return {"ok": False, "error":"empty"}
    out=compute(df.copy())
    return {"ok": True, "indicators": out.reset_index().to_dict(orient="list")}
