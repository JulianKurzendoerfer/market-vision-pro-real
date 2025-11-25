from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import yfinance as yf
from indicators import compute_indicators

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def df_from_yf(symbol: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    df = df[["Open","High","Low","Close","Volume"]].copy()
    df.index.name = "Date"
    return df

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = "AAPL", range: str = "1y", interval: str = "1d"):
    df = df_from_yf(symbol, range, interval)
    if df.empty:
        return {"ok": False, "error": "no data"}
    meta = {"symbol": symbol, "range": range, "interval": interval}
    out = df.reset_index().assign(Date=lambda x: x["Date"].astype(str)).to_dict(orient="records")
    return {"ok": True, "meta": meta, "ohlc": out}

@app.post("/v1/compute")
def v1_compute(body: dict = Body(...)):
    if isinstance(body, dict) and "ohlc" in body:
        df = pd.DataFrame(body["ohlc"])
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
    else:
        symbol = body.get("symbol","AAPL") if isinstance(body, dict) else "AAPL"
        rng = body.get("range","1y") if isinstance(body, dict) else "1y"
        interval = body.get("interval","1d") if isinstance(body, dict) else "1d"
        df = df_from_yf(symbol, rng, interval)
    if df is None or df.empty:
        return {"ok": False, "error": "empty"}
    ind = compute_indicators(df.dropna().copy())
    return {"ok": True, "indicators": ind.reset_index(drop=True).astype(float).round(6).to_dict(orient="list")}
