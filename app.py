import os, time, datetime as dt, requests, pandas as pd
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
    if r=="1Y": return now-dt.timedelta(days=365)
    if r=="2Y": return now-dt.timedelta(days=365*2)
    if r=="5Y": return now-dt.timedelta(days=365*5)
    return now-dt.timedelta(days=365)

def _df_from_ohlc(d):
    df=pd.DataFrame(d)
    if "t" in df.columns: df["Date"]=pd.to_datetime(df["t"],unit="s")
    if "date" in df.columns: df["Date"]=pd.to_datetime(df["date"])
    df=df.set_index("Date").sort_index()
    cols=[c for c in ["Open","High","Low","Close","Volume","Adj Close"] if c in df.columns]
    if not cols and {"o","h","l","c"}<=set(df.columns):
        df=df.rename(columns={"o":"Open","h":"High","l":"Low","c":"Close","v":"Volume"})
        cols=["Open","High","Low","Close","Volume"]
    return df[cols]

def _fetch(sym, rng):
    key=(sym,rng)
    if key in _CACHE and time.time()-_CACHE[key][0] < 300:
        return _CACHE[key][1]
    if not API: return []
    fr=_rng_to_from(rng).strftime("%Y-%m-%d")
    url=f"https://eodhd.com/api/eod/{sym}?from={fr}&fmt=json&api_token={API}"
    r=requests.get(url,timeout=30)
    if r.status_code!=200: return []
    data=r.json()
    if isinstance(data,dict) and data.get("code")==400: return []
    _CACHE[key]=(time.time(),data)
    return data

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
def bundle(symbol: str="AAPL", range: str="1Y", interval: str="1d", adjust: bool=True):
    data=_fetch(symbol, range)
    if not data: return {"ok": False, "error": "upstream or empty"}
    df=_df_from_ohlc(data)
    if len(df)==0: return {"ok": False, "error": "no data"}
    out=compute(df.dropna().copy())
    meta={"symbol":symbol,"range":range,"interval":interval}
    ohlc=df.reset_index().rename(columns={"index":"Date"})
    ohlc["Date"]=pd.to_datetime(ohlc["Date"]).dt.strftime("%Y-%m-%d")
    return {"ok": True, "meta": meta, "ohlc": ohlc.to_dict(orient="records"), "ind": out}

@app.post("/v1/compute")
def v1_compute(body:dict=...):
    if isinstance(body,dict) and "ohlc" in body:
        df=pd.DataFrame(body["ohlc"])
        df=df.rename(columns={"Open":"Open","High":"High","Low":"Low","Close":"Close","Volume":"Volume"})
        if "Date" in df.columns: df["Date"]=pd.to_datetime(df["Date"]); df=df.set_index("Date")
    else:
        symbol=body.get("symbol","AAPL") if isinstance(body,dict) else "AAPL"
        rng=body.get("range","1Y") if isinstance(body,dict) else "1Y"
        interval=body.get("interval","1d") if isinstance(body,dict) else "1d"
        df=_df_from_ohlc(_fetch(symbol,rng))
    if df is None or df.empty: return {"ok": False, "error": "empty"}
    ind=compute(df.dropna().copy())
    out={"k": ind.reset_index(drop=True).astype(float).round(6).to_dict(orient="records")}
    return {"ok": True, "indicators": out}
