import os, math, unicodedata
from datetime import datetime, timezone, date
import requests, pandas as pd, numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

EOD_KEY=os.environ.get("EODHD_API_KEY","")
ALLOWED=os.environ.get("ALLOWED_ORIGINS","*").split(",")

app=FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=[o.strip() for o in ALLOWED if o.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

def norm(s): return unicodedata.normalize("NFKD",(s or "")).encode("ascii","ignore").decode().strip().lower()

@app.get("/health")
def health(): return {"ok":True,"asof":datetime.now(timezone.utc).isoformat()}

def eod_search(q,limit=25,typ="stock"):
    u=f"https://eodhd.com/api/search/{q}"
    p={"api_token":EOD_KEY,"fmt":"json","limit":limit,"type":typ}
    r=requests.get(u,params=p,timeout=8)
    if r.status_code!=200: raise HTTPException(502,"search_http")
    d=r.json()
    if not isinstance(d,list): raise HTTPException(502,"search_shape")
    out=[]
    for x in d: out.append({"code":x.get("Code"),"exchange":x.get("Exchange"),"name":x.get("Name"),"currency":x.get("Currency"),"isPrimary":x.get("isPrimary")})
    return out

US_PREF=["NASDAQ","NYSE","AMEX","BATS","US"]
EU_PREF=["XETRA","FRA","LSE","PAR","MIL","AMS","VIE","SWX"]

def resolve_symbol(q,prefer="US"):
    qc=q.strip()
    if "." in qc and len(qc.split("."))==2:
        c,e=qc.upper().split("."); return {"input":qc,"symbol":f"{c}.{e}","exchange":e,"name":qc}
    it=eod_search(qc)
    if not it: raise HTTPException(404,"no_matches")
    qn=norm(qc); pref=US_PREF if prefer.upper()=="US" else EU_PREF
    def score(x):
        exact_symbol=((x["code"] or "").upper()==qc.upper())
        exact_name=(norm(x["name"])==qn)
        sym_starts=((x["code"] or "").upper().startswith(qc.upper()))
        name_contains=(qn in norm(x["name"]))
        exch_rank=2 if (x["exchange"] or "").upper() in pref else 0
        is_primary=1 if x.get("isPrimary") else 0
        usd=1 if (x.get("currency") or "").upper()=="USD" else 0
        return (5 if exact_symbol else 0,4 if exact_name else 0,3 if sym_starts else 0,2 if name_contains else 0,is_primary,exch_rank,usd)
    t=sorted(it,key=score,reverse=True)[0]
    sym=f"{t['code']}.{t['exchange']}".upper()
    return {"input":qc,"symbol":sym,"exchange":t["exchange"],"name":t["name"]}

def eod_intraday(symbol,interval="60m",days=10,timeout=8,retries=3):
    u=f"https://eodhd.com/api/intraday/{symbol}"
    p={"api_token":EOD_KEY,"fmt":"json","interval":interval,"range":f"{days}d"}
    back=0.8
    for _ in range(retries):
        try:
            r=requests.get(u,params=p,timeout=timeout)
            if r.status_code==200:
                arr=r.json()
                if not isinstance(arr,list) or not arr: raise ValueError("empty")
                rows=[]
                for x in arr:
                    ts=datetime.fromtimestamp(int(x["timestamp"]),tz=timezone.utc)
                    o=float(x["open"]);h=float(x["high"]);l=float(x["low"]);c=float(x["close"]);v=float(x.get("volume") or 0)
                    if not (l<=min(o,c) and h>=max(o,c) and v>=0): continue
                    rows.append((ts,o,h,l,c,v))
                rows.sort(key=lambda z:z[0])
                if not rows: raise ValueError("no_rows")
                step={"1m":60,"5m":300,"15m":900,"30m":1800,"60m":3600}.get(interval,3600)
                if (datetime.now(timezone.utc)-rows[-1][0]).total_seconds()<step*0.8: rows=rows[:-1] or rows
                return rows
        except Exception: pass
        import time; time.sleep(back); back*=1.8
    raise HTTPException(502,"upstream_unavailable")

def to_df(rows):
    ts=[r[0] for r in rows]
    return pd.DataFrame(rows,columns=["ts","o","h","l","c","v"]).set_index(pd.DatetimeIndex(ts))

def ema(s,span): return s.ewm(span=span,adjust=False).mean()

def rsi(close,length=14):
    d=close.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/length,min_periods=length,adjust=False).mean()
    ad=dn.ewm(alpha=1/length,min_periods=length,adjust=False).mean()
    rs=au/(ad.replace(0,np.nan)); return 100-(100/(1+rs))

def stoch_kd(h,l,c,k=14,d=3,smooth=3):
    ll=l.rolling(k).min(); hh=h.rolling(k).max()
    raw=100*(c-ll)/(hh-ll); kline=raw.rolling(smooth).mean(); dline=kline.rolling(d).mean()
    return kline.fillna(method="bfill"),dline.fillna(method="bfill")

def macd(close,fast=12,slow=26,signal=9):
    e1=ema(close,fast); e2=ema(close,slow); m=e1-e2; s=ema(m,signal); h=m-s; return m,s,h

def bb(close,ma=20,mult=2.0):
    m=close.rolling(ma).mean(); sd=close.rolling(ma).std(ddof=0); ub=m+mult*sd; lb=m-mult*sd; return m,ub,lb

SNAP={}

@app.get("/v1/resolve")
def api_resolve(q: str, prefer: str="US"): return resolve_symbol(q,prefer)

@app.get("/v1/ohlcv")
def api_ohlcv(symbol: str, interval: str="60m"):
    key=(symbol.upper(),interval)
    try:
        rows=eod_intraday(symbol,interval=interval,days=10); df=to_df(rows)
        payload={"symbol":symbol.upper(),"interval":interval,"bars":[{"ts":i.isoformat(),"o":float(r.o),"h":float(r.h),"l":float(r.l),"c":float(r.c),"v":float(r.v)} for i,r in df.iterrows()]}
        SNAP[key]=payload; return payload
    except HTTPException:
        snap=SNAP.get(key)
        if snap: return snap
        raise

@app.get("/v1/indicators")
def api_ind(symbol: str, interval: str="60m"):
    try: rows=eod_intraday(symbol,interval=interval,days=10); df=to_df(rows)
    except HTTPException:
        key=(symbol.upper(),interval); snap=SNAP.get(key)
        if not snap: raise
        idx=pd.to_datetime([b["ts"] for b in snap["bars"]])
        df=pd.DataFrame([{k:float(b[k]) for k in ["o","h","l","c","v"]} for b in snap["bars"]],index=idx)
    c=df["c"]; h=df["h"]; l=df["l"]
    m,ub,lb=bb(c,20,2.0); k,d=stoch_kd(h,l,c,14,3,3); r=rsi(c,14); mac,sg,hist=macd(c,12,26,9); hs=hist.diff()
    last={"bb":{"ma":float(m.iloc[-1]),"ub":float(ub.iloc[-1]),"lb":float(lb.iloc[-1]),"c":float(c.iloc[-1])},
          "stoch":{"k":float(k.iloc[-1]),"d":float(d.iloc[-1])},
          "rsi":{"val":float(r.iloc[-1])},
          "macd":{"macd":float(mac.iloc[-1]),"signal":float(sg.iloc[-1]),"hist":float(hist.iloc[-1]),"slope":float(hs.iloc[-1])}}
    return {"symbol":symbol.upper(),"interval":interval,"values":last}

def std_norm_cdf(x):
    from math import erf, sqrt
    return 0.5*(1+erf(x/sqrt(2)))

def black_scholes_delta(is_call,S,K,T,r,sigma):
    if sigma<=0 or T<=0: return 0.0
    d1=(math.log(S/K)+(r+0.5*sigma*sigma)*T)/(sigma*math.sqrt(T))
    from math import erf, sqrt
    cdf=0.5*(1+erf(d1/sqrt(2)))
    if is_call: return cdf
    return cdf-1

def pop_from_bs(is_put,S,K,T,r,sigma):
    if sigma<=0 or T<=0: return 0.5
    d2=(math.log(S/K)+(r-0.5*sigma*sigma)*T)/(sigma*math.sqrt(T))
    p=std_norm_cdf(d2)
    return p if is_put else 1-p

def yf_symbol_from_eod(s):
    s=s.upper()
    if s.endswith(".US"): return s.split(".")[0]
    if s.endswith(".XETRA") or s.endswith(".FRA"): return s.split(".")[0]+".DE"
    if s.endswith(".LSE"): return s.split(".")[0]+".L"
    return s.split(".")[0]

@app.get("/v1/options/ladder")
def ladder(symbol: str, side: str="puts", dte: str="7-14", n: int=14):
    import yfinance as yf
    yf_sym=yf_symbol_from_eod(symbol)
    t=yf.Ticker(yf_sym)
    spot=t.fast_info["last_price"] if "last_price" in t.fast_info else float(t.history(period="1d")["Close"].iloc[-1])
    exps=t.options
    if not exps: raise HTTPException(502,"no_options")
    lo,hi=[int(x) for x in dte.split("-")]
    today=date.today()
    sel=[e for e in exps if lo<= (datetime.fromisoformat(e).date()-today).days <=hi]
    if not sel: raise HTTPException(404,"no_expiry_in_range")
    expiry=sorted(sel,key=lambda s:abs((datetime.fromisoformat(s).date()-today).days))[0]
    ch=t.option_chain(expiry)
    df=(ch.puts if side=="puts" else ch.calls).copy()
    df["mid"]=(df["bid"]+df["ask"])/2
    df=df.replace([np.inf,-np.inf],np.nan).dropna(subset=["strike","mid"])
    T=max(1,(datetime.fromisoformat(expiry).date()-today).days)/365; r=0.04
    iv=np.array(df["impliedVolatility"].fillna(0.3)); K=np.array(df["strike"]); S=float(spot)
    if side=="puts":
        delta=np.array([black_scholes_delta(False,S,float(k),T,r,float(max(0.05,float(ivv)))) for k,ivv in zip(K,iv)])
        df["delta"]=delta; df=df[(df["delta"]<=-0.10)&(df["delta"]>=-0.30)]
        df["otm_pct"]=(S-df["strike"])/S*100; df=df[df["otm_pct"]>=5.0]
        df["yield_weekly_pct"]=df["mid"]/df["strike"]; df=df[(df["yield_weekly_pct"]*100<=5.0)]
        df["pop_pct"]=np.clip(np.array([pop_from_bs(True,S,float(k),T,r,float(max(0.05,float(ivv)))) for k,ivv in zip(K,iv)])*100,0,100)
    else:
        delta=np.array([black_scholes_delta(True,S,float(k),T,r,float(max(0.05,float(ivv)))) for k,ivv in zip(K,iv)])
        df["delta"]=delta; df=df[(df["delta"]>=0.10)&(df["delta"]<=0.30)]
        df["otm_pct"]=(df["strike"]-S)/S*100; df=df[df["otm_pct"]>=5.0]
        df["yield_weekly_pct"]=df["mid"]/S; df=df[(df["yield_weekly_pct"]*100<=5.0)]
        df["pop_pct"]=np.clip(np.array([pop_from_bs(False,S,float(k),T,r,float(max(0.05,float(ivv)))) for k,ivv in zip(K,iv)])*100,0,100)
    for c in ["openInterest","volume"]:
        if c not in df.columns: df[c]=0
    df["spread_pct"]=np.where(df["mid"]>0,(df["ask"]-df["bid"])/df["mid"]*100,999)
    df=df[(df["openInterest"]>=500)&(df["volume"]>=50)&(df["spread_pct"]<=5)]
    df=df.sort_values(by=["pop_pct","yield_weekly_pct","otm_pct"],ascending=[False,False,False]).head(max(1,min(n,20)))
    rows=[]
    for _,r in df.iterrows():
        risk="low"
        if r["pop_pct"]<80 or abs(r.get("delta",0))>0.20: risk="medium"
        if r["pop_pct"]<70: risk="high"
        rows.append({"expiry":expiry,"dte":int(max(1,(datetime.fromisoformat(expiry).date()-date.today()).days)),"strike":float(r["strike"]),"delta":float(r.get("delta",0)),"premium":float(r["mid"]),"yield_weekly_pct":float(np.round(r["yield_weekly_pct"]*100,2)),"otm_pct":float(np.round(r["otm_pct"],2)),"pop_pct":float(np.round(r["pop_pct"],2)),"spread_pct":float(np.round(r["spread_pct"],2)),"oi":int(r["openInterest"]),"vol":int(r["volume"]),"risk":risk})
    return {"symbol":symbol.upper(),"side":side,"spot":float(np.round(spot,2)),"expiry":expiry,"rows":rows}
