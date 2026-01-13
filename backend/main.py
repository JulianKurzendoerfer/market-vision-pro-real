from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/quote")
def quote(ticker: str = Query(..., min_length=1, max_length=15)):
    t = yf.Ticker(ticker)
    info = t.fast_info
    price = info.get("last_price")
    currency = info.get("currency")
    return {"ticker": ticker.upper(), "price": price, "currency": currency}
