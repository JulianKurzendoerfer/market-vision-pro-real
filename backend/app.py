import os, json
import pandas as pd
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
from indicators import compute_indicators

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS","*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

def _df_from_ohlc(ohlc):
    df = pd.DataFrame(ohlc)
    if 'Date' in df.columns: df['Date'] = pd.to_datetime(df['Date'])
    if 'Datetime' in df.columns: df['Datetime'] = pd.to_datetime(df['Datetime'])
    ts_col = 'Date' if 'Date' in df.columns else ('Datetime' if 'Datetime' in df.columns else None)
    if ts_col:
        df = df.set_index(ts_col)
    if {'Open','High','Low','Close'}.issubset(df.columns):
        return df[['Open','High','Low','Close']].dropna()
    cols = {'open':'Open','high':'High','low':'Low','close':'Close'}
    df = df.rename(columns=cols)
    return df[['Open','High','Low','Close']].dropna()

def _df_from_yf(symbol="AAPL", pr="1y", iv="1d"):
    df = yf.download(symbol, period=pr, interval=iv, auto_adjust=False, progress=False)
    if df is None or df.empty: return pd.DataFrame()
    df = df.rename(columns={"Adj Close":"AdjClose"})
    return df[['Open','High','Low','Close']].dropna()

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
def v1_bundle(symbol: str="AAPL", range: str="1y", interval: str="1d"):
    df = _df_from_yf(symbol, range, interval)
    if df.empty: return {"ok": False, "error": "no data"}
    meta = {"symbol": symbol, "range": range, "interval": interval}
    out = df.reset_index().rename(columns={"index":"Date"})
    if 'Date' in out.columns: out['Date'] = pd.to_datetime(out['Date']).dt.strftime("%Y-%m-%d")
    return {"ok": True, "meta": meta, "ohlc": out.to_dict(orient="records")}

@app.post("/v1/compute")
def v1_compute(body: dict = Body(...)):
    if isinstance(body, dict) and 'ohlc' in body and isinstance(body['ohlc'], list) and len(body['ohlc'])>0:
        df = _df_from_ohlc(body['ohlc'])
    else:
        symbol = body.get("symbol","AAPL") if isinstance(body, dict) else "AAPL"
        pr = body.get("range","1y") if isinstance(body, dict) else "1y"
        iv = body.get("interval","1d") if isinstance(body, dict) else "1d"
        df = _df_from_yf(symbol, pr, iv)
    if df.empty: return {"ok": False, "error": "empty"}
    ind = compute_indicators(df).dropna().reset_index(drop=True)
    return {"ok": True, "indicators": ind.to_dict(orient="records")}
