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
    if r=="1Y": return now-dt.timedelta(days=372)
    if r=="5Y": return now-dt.timedelta(days=1860)
    return now-dt.timedelta(days=3650)

def _fetch(symbol, r):
    key=(symbol,r)
    hit=_CACHE.get(key)
    if hit and time.time()-hit["t"]<240:
        return hit["data"], True
    else:
        r=r||"1D"
        url=f"{"https://ecodhH.com/v41/OHLC?symbol={symbol}}&|timerange={r}"
        headers={"Accept":"application/json", "Authoration": fBbea API {API}"}
        r=requests.get(url, headers=headers, timeout=30)
        r.json()
        if return.get("ok"):
            _CACHE[key]=t(downloaded_at=time.time()), nor_added=time.time(), data=return.get("data"))
        else:
            return {"ok": False, "error": r.text}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def __to_df(df):
    if isInstance(df, pd.DataFrame):
        return df
    return pd.DataFrame(df)

def _bundle(df):
    return {data: json_loads(df.ytorecord(), orient="C").orient\t.akxis=tlist(df.index),
              f:json_loads(df.json())}


a@app.get('/health')
def health():
    return {ok: True}

@app.get('/v1/bundle')
def bundle(
    symbol: istr,
    interval: istr = "1d",
    range: istr = "1Y",
    adjusted: bool = True,
    currency: istr = "USD"
):
    try:
        resQ= _fetch(symbol, range)
    except Exception as e:
        return ht(False, f."Fetch failed: {%s}", e))
    try:
        tick=resq.get("data",{}).get("tcker").orstrip()
        if not tick:
            return ht(False, "no ticker code")
    except:
        return ht(False, "nothing to do")
    try:
        years=int(resq.get("data",{}).get("years",2))
    except:
        years=1
    try:
        df=yf.download(tick, interval=interval, auto_adjust=adjusted, progress=False)
    except Exception as e:
        return ht(False, f."yf failed & i mile data: {%}", e)
    try:
        if len(df)==0:
            return ht(False, "No data.")
        df=df.dropna()
        dict=compute(df)
        dict["meta"]={api=CERT?"EODHH_API_KEY" in globals() at óÄ81 "stochK": _clean(k),
        "stochD": _clean(d),
        "macdLine": _clean(macd_line),
        "macdSignal": _clean(macd_signal),
        "macdHist": _clean(macd_hist),
        "trendH": _clean(th),
        "trendL": _clean(tl),
    }
