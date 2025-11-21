import numpy as np, pandas as pd

def _ema(s,n): return s.ewm(span=n,adjust=False).mean()
def _sma(s,n): return s.rolling(n).mean()

def _rsi(c,n=14):
    d=c.diff()
    up=d.clip(lower=0)
    dn=(-d).clip(lower=0)
    rs=_ema(up,n)/_ema(dn,n).replace(0,np.nan)
    return 100-(100/(1+rs))

def _stoch(c,h,l,k=14,d=3,smooth=3):
    ll=l.rolling(k).min()
    hh=h.rolling(k).max()
    kraw=100*(c-ll)/(hh-ll)
    K=kraw.rolling(smooth).mean()
    D=K.rolling(d).mean()
    return K,D

def _macd(c,fast=12,slow=26,signal=9):
    line=_ema(c,fast)-_ema(c,slow)
    sig=line.ewm(span=signal,adjust=False).mean()
    hist=line-sig
    return line,sig,hist

def _trendhl(h,l,n=20):
    return h.rolling(n).max(), l.rolling(n).min()

def _boll(c,n=20,k=2.0):
    basis=_sma(c,n)
    std=c.rolling(n).std(ddof=0)
    upper=basis+k*std
    lower=basis-k*std
    return basis,upper,lower

def _clean(s):
    if isinstance(s,list): arr=s
    else: arr=list(pd.Series(s,dtype="float64"))
    out=[]
    for v in arr:
        if v is None: out.append(None); continue
        try:
            x=float(v)
            if np.isfinite(x): out.append(x)
            else: out.append(None)
        except: out.append(None)
    return out

def _cross_up(a,b):
    z=[]
    for i in range(1,len(a)):
        pa=a[i-1]; pb=b[i-1]; ca=a[i]; cb=b[i]
        if pa is None or pb is None or ca is None or cb is None: continue
        if pa<=pb and ca>cb: z.append(i)
    return z

def _cross_dn(a,b):
    z=[]
    for i in range(1,len(a)):
        pa=a[i-1]; pb=b[i-1]; ca=a[i]; cb=b[i]
        if pa is None or pb is None or ca is None or cb is None: continue
        if pa>=pb and ca<cb: z.append(i)
    return z

def compute_frame(df,t=None):
    c=df["close"].astype("float64")
    h=df["high"].astype("float64")
    l=df["low"].astype("float64")
    ema20=_ema(c,20)
    ema50=_ema(c,50)
    rsi=_rsi(c,14)
    stK,stD=_stoch(c,h,l,14,3,3)
    macL,macS,macH=_macd(c,12,26,9)
    tH,tL=_trendhl(h,l,20)
    bbB,bbU,bbL=_boll(c,20,2.0)
    out={
        "ema20":_clean(ema20),
        "ema50":_clean(ema50),
        "rsi":_clean(rsi),
        "stochK":_clean(stK),
        "stochD":_clean(stD),
        "macdLine":_clean(macL),
        "macdSignal":_clean(macS),
        "macdHist":_clean(macH),
        "trendH":_clean(tH),
        "trendL":_clean(tL),
        "bbBasis":_clean(bbB),
        "bbUpper":_clean(bbU),
        "bbLower":_clean(bbL)
    }
    tt=list(t) if t is not None else [None]*len(out["ema20"])
    k=_clean(stK); d=_clean(stD)
    r=_clean(rsi)
    ml=_clean(macL); ms=_clean(macS)
    sx=[]
    for i in _cross_up(k,[20]*len(k)): sx.append({"i":i,"t":tt[i] if i<len(tt) else None,"type":"stoch_buy"})
    for i in _cross_dn(k,[80]*len(k)): sx.append({"i":i,"t":tt[i] if i<len(tt) else None,"type":"stoch_sell"})
    for i in _cross_up(r,[30]*len(r)): sx.append({"i":i,"t":tt[i] if i<len(tt) else None,"type":"rsi_buy"})
    for i in _cross_dn(r,[70]*len(r)): sx.append({"i":i,"t":tt[i] if i<len(tt) else None,"type":"rsi_sell"})
    for i in _cross_up(ml,ms): sx.append({"i":i,"t":tt[i] if i<len(tt) else None,"type":"macd_buy"})
    for i in _cross_dn(ml,ms): sx.append({"i":i,"t":tt[i] if i<len(tt) else None,"type":"macd_sell"})
    out["signals"]=sx
    return out

def compute_from_ohlcv(ohlcv):
    c=ohlcv.get("c") or ohlcv.get("close") or []
    h=ohlcv.get("h") or ohlcv.get("high") or []
    l=ohlcv.get("l") or ohlcv.get("low") or []
    t=ohlcv.get("t") or ohlcv.get("time") or None
    n=min(len(c),len(h),len(l))
    df=pd.DataFrame({"close":c[:n],"high":h[:n],"low":l[:n]})
    return compute_frame(df,t[:n] if t else None)
