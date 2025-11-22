from fastapi import FastAPI, Body
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np
import yfinance as yf
from backend.indicators import compute_indicators

app = FastAPI()

class BodyModel(BaseModel):
    o: list[float] = Field(default_factory=list)
    h: list[float] = Field(default_factory=list)
    l: list[float] = Field(default_factory=list)
    c: list[float] = Field(default_factory=list)
    v: list[float] = Field(default_factory=list)
    i: list[str]   = Field(default_factory=list)

def _to_df(d: BodyModel) -> pd.DataFrame:
    try:
        df = pd.DataFrame(dict(
            Open  = d.o,
            High  = d.h,
            Low   = d.l,
            Close = d.c,
            Volume= d.v if d.v else [0.0]*len(d.c),
            Index = d.i,
        ))
        if len(df) == 0:
            return df
        if df["Index"].notna().all() and df["Index"].astype(str).str.len().gt(0).all():
            df["Index"] = pd.to_datetime(df["Index"], errors="coerce")
            df = df.set_index("Index")
        else:
            df = df.drop(columns=["Index"], errors="ignore")
        df = df.dropna()
        return df
    except Exception:
        return pd.DataFrame()

def _bundle(df: pd.DataFrame) -> dict:
    try:
        res = compute_indicators(df)
        out = dict(
            ok=True,
            o=df["Open"].round(4).tolist()  if "Open"  in df else [],
            h=df["High"].round(4).tolist()  if "High"  in df else [],
            l=df["Low"].round(4).tolist()   if "Low"   in df else [],
            c=df["Close"].round(4).tolist() if "Close" in df else [],
            v=df.get("Volume", pd.Series(dtype=float)).fillna(0).astype(float).round(3).tolist() if "Volume" in df else [],
            i=[str(x) for x in df.index],
            ind={k: [None if pd.isna(x) else float(x) for x in v] for k, v in res.items()}
        )
        return out
    except Exception as e:
        return {"ok": False, "error": f"bundle_failed: {e}"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/bundle")
def v1_bundle(symbol: str = "AAPL", range: str = "1y", interval: str = "1d", adj: bool = True):
    try:
        df = yf.download(symbol, period=range, interval=interval, auto_adjust=adj, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.dropna().copy()
        df.index = pd.to_datetime(df.index)
    except Exception as e:
        return {"ok": False, "error": f"yfinance_failed: {e}"}
    if df.empty:
        return {"ok": False, "error": "empty"}
    return _bundle(df)

@app.post("/v1/compute")
def v1_compute(body: Body = Body(...)):
    d = BodyModel(**body)
    df = _to_df(d)
    if df.empty:
        return {"ok": False, "error": "empty"}
    return _bundle(df)
