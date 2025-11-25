import pandas as pd, numpy as np

def ema(s, n):
    return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    d=close.diff()
    up=d.clip(lower=0)
    dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/n, adjust=False).mean()
    ad=dn.ewm(alpha=1/n, adjust=False).mean()
    rs=au/ad.replace(0,np.nan)
    return 100-100/(1+rs)

def macd_tv(close, fast=12, slow=26, sig=9):
    ema_f=ema(close,fast)
    ema_s=ema(close,slow)
    macd=ema_f-ema_s
    sigl=ema(macd,sig)
    hist=macd-sigl
    return macd, sigl, hist

def stoch_rsi(close, k=14, d=3, smooth_k=3):
    rsi=rsi_wilder(close, n=k)
    min_r=rsi.rolling(k).min()
    max_r=rsi.rolling(k).max()
    st_k=(rsi-min_r)/(max_r-min_r+1e-9)*100
    st_k=st_k.rolling(smooth_k).mean()
    st_d=st_k.rolling(d).mean()
    return st_k, st_d

def bbands(close, n=20, mult=2):
    ma=close.rolling(n).mean()
    sd=close.rolling(n).std()
    upper=ma+mult*sd
    lower=ma-mult*sd
    return ma, upper, lower, sd

def atr(h,l,c,n=14):
    tr=pd.concat([(h-l).abs(), (h-c.shift(1)).abs(), (l-c.shift(1)).abs()],axis=1).max(axis=1)
    return tr.rolling(n).mean()

def psar(h,l, step=0.02, max_step=0.2):
    sar = l.shift(1)
    ep = h.copy()
    af = pd.Series(step, index=h.index)
    bull = pd.Series(True, index=h.index)
    for i in range(2,len(h)):
        af.iloc[i]=af.iloc[i-1]
        bull.iloc[i]=bull.iloc[i-1]
        ep.iloc[i]=ep.iloc[i-1]
        sar.iloc[i]=sar.iloc[i-1] + af.iloc[i-1]*(ep.iloc[i-1]-sar.iloc[i-1])
        if bull.iloc[i-1]:
            sar.iloc[i]=min(sar.iloc[i], l.iloc[i-1], l.iloc[i-2])
            if h.iloc[i] > ep.iloc[i-1]:
                ep.iloc[i]=h.iloc[i]
                af.iloc[i]=min(max_step, af.iloc[i-1]+step)
            if l.iloc[i] < sar.iloc[i]:
                bull.iloc[i]=False
                sar.iloc[i]=ep.iloc[i-1]
                ep.iloc[i]=l.iloc[i]
                af.iloc[i]=step
        else:
            sar.iloc[i]=max(sar.iloc[i], h.iloc[i-1], h.iloc[i-2])
            if l.iloc[i] < ep.iloc[i-1]:
                ep.iloc[i]=l.iloc[i]
                af.iloc[i]=min(max_step, af.iloc[i-1]+step)
            if h.iloc[i] > sar.iloc[i]:
                bull.iloc[i]=True
                sar.iloc[i]=ep.iloc[i-1]
                ep.iloc[i]=h.iloc[i]
                af.iloc[i]=step
    return sar

def compute(df):
    c=df["Close"]; h=df["High"]; l=df["Low"]
    out=pd.DataFrame(index=df.index)
    out["EMA20"]=ema(c,20); out["EMA50"]=ema(c,50); out["EMA200"]=ema(c,200)
    out["RSI"]=rsi_wilder(c,14)
    m,s,h=macd_tv(c,12,26,9)
    out["MACD"]=m; out["MACD_sig"]=s; out["MACD_hist"]=h
    kf,df_=stoch_rsi(c,14,3,3)
    out["%K"]=kf; out["%D"]=df_
    ma,up,low,sd=bbands(c,20,2)
    out["BB_mid"]=ma; out["BB_up"]=up; out["BB_low"]=low
    out["ATR14"]=atr(h,l,c,14)
    out["PSAR"]=psar(h,l)
    return out
