import numpy as np
import pandas as pd

def _ema(s:pd.Series,n:int)->pd.Series:
    return s.ewm(span=n,adjust=False).mean()

def _rsi(c:pd.Series,n:int=14)->pd.Series:
    d=c.diff()
    up=d.clip(lower=0)
    dn=(-d).clip(lower=0)
    roll_up=up.ewm(alpha=1/n,adjust=False).mean()
    roll_dn=dn.ewm(alpha=1/n,adjust=False).mean()
    rs=roll_up/roll_dn.replace(0,np.nan)
    return 100-(100/(1+rs))

def _stoch(c:pd.Series,h:pd.Series,l:pd.Series,n:int=14,k:int=3,d:int=3):
    ll=l.rolling(n).min()
    hh=h.rolling(n).max()
    raw_k=100*(c-ll)/(hh-ll)
    stoch_k=raw_k.rolling(k).mean()
    stoch_d=stoch_k.rolling(d).mean()
    return stoch_k,stoch_d

def _macd(c:pd.Series,f:int=12,s:int=26,sig:int=9):
    ef=_ema(c,f)
    es=_ema(c,s)
    line=ef-es
    signal=line.ewm(span=sig,adjust=False).mean()
    hist=line-signal
    return line,signal,hist

def _boll(c:pd.Series,n:int=20,z:float=2.0):
    mid=c.rolling(n).mean()
    std=c.rolling(n).std(ddof=0)
    up=mid+z*std
    dn=mid-z*std
    return mid,up,dn

def _clean(s:pd.Series):
    return s.replace([np.inf,-np.inf],np.nan).astype(float).where(pd.notna(s),None).tolist()

def compute_indicators(df:pd.DataFrame)->dict:
    c=df["c"].astype(float)
    h=df["h"].astype(float) if "h" in df else c
    l=df["l"].astype(float) if "l" in df else c
    ema20=_ema(c,20)
    ema50=_ema(c,50)
    rsi14=_rsi(c,14)
    k,d=_stoch(c,h,l,14,3,3)
    macLine,macSignal,macHist=_macd(c,12,26,9)
    bbMid,bbUp,bbDn=_boll(c,20,2.0)
    trendH=h.rolling(20).max()
    trendL=l.rolling(20).min()
    return {
        "ema20":_clean(ema20),
        "ema50":_clean(ema50),
        "rsi14":_clean(rsi14),
        "stochK":_clean(k),
        "stochD":_clean(d),
        "macLine":_clean(macLine),
        "macSignal":_clean(macSignal),
        "macHist":_clean(macHist),
        "bbMid":_clean(bbMid),
        "bbUp":_clean(bbUp),
        "bbDn":_clean(bbDn),
        "trendH":_clean(trendH),
        "trendL":_clean(trendL)
    }
