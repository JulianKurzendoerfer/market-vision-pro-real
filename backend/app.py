import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from typing import List, Optional
from indicators import compute_indicators

class Bar(BaseModel):
    t: Optional[str] = None
    o: float
    h: float
    l: float
    c: float

class Body(BaseModel):
    ohlc: List[Bar]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/v1/compute")
def v1_compute(body: Body):
    rows = [{"Open":b.o, "High":b.h, "Low":b.l, "Close":b.c} for b in body.ohlc]
    if not rows:
        return {"ok": False, "error": "empty"}
    df = pd.DataFrame(rows)
    out = compute_indicators(df).reset_index(drop=True)
    return {"ok": True, "indicators": out.to_dict(orient="records")}
