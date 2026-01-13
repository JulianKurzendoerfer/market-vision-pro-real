import numpy as np, pandas as pd

def ema(s, n): return s.ewm(span=int(n), adjust=False).mean()

def rsi_wilder(close, n=14):
    d=close.diff()
    up=d.clip(lower=0)
    dn=-d.clip(upper=0)
    rs=ema(up,n)/ema(dn,n)
    return 100-(100/(1+rs))

def macd(cv, f=12, s=26, m=9):
    f_=ema(cv,f); s_=ema(cv,s); m_=ema(f_-s_,m)
    return f_-s_, m_, f_-s_-m_

def stoch_rsi(c, k=14, d=3, s=3):
    r=rsi_wilder(c,k)
    st=(r-r.rolling(k).min())/(r.rolling(k).max()-r.rolling(k).min())
    kf=st.rolling(d).mean()
    df=kf.rolling(s).mean()
    return kf, df

def atr(h,l,c,n=14):
    tr=pd.concat([(h-l).abs(), (h-c.shift()).abs(), (l-c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def psar(h,l, af=0.02, af_max=0.2):
    sar=h.copy()*0; bull=True; ep=l.iloc[0]; sar.iloc[0]=l.iloc[0]; a=af
    for i in range(1,len(h)):
        prev=sar.iloc[i-1]
        sar.iloc[i]=prev+a*(ep-prev)
        if bull:
            if l.iloc[i]<sar.iloc[i]:
                bull=False; sar.iloc[i]=ep; ep=l.iloc[i]; a=0.02
            else:
                if h.iloc[i]>ep: ep=h.iloc[i]; a=min(af_max,a+af)
                sar.iloc[i]=min(sar.iloc[i], l.iloc[i-1], l.iloc[i-2] if i>1 else l.iloc[i-1])
        else:
            if h.iloc[i]>sar.iloc[i]:
                bull=True; sar.iloc[i]=ep; ep=h.iloc[i]; a=0.02
            else:
                if l.iloc[i]<ep: ep=l.iloc[i]; a=min(af_max,a+af)
                sar.iloc[i]=max(sar.iloc[i], h.iloc[i-1], h.iloc[i-2] if i>1 else h.iloc[i-1])
    return sar

def compute(df):
    c=df["Close"]; h=df["High"]; l=df["Low"]
    out=pd.DataFrame(index=df.index)
    out["EMA20"]=ema(c,20); out["EMA50"]=ema(c,50); out["EMA200"]=ema(c,200)
    out["RSI"]=rsi_wilder(c,14)
    mc, ms, mh = macd(c)
    out["MACD"]=mc; out["MACD_sig"]=ms; out["MACD_hist"]=mh
    kf, df_ = stoch_rsi(c,14,3,3)
    out["ST_RSI_K"]=kf; out["ST_RSI_D"]=df_
    out["ATR20"]=atr(h,l,c,20)
    return out.reset_index()
