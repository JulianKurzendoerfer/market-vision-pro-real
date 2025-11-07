import os, requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS","*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/v1/resolve")
def resolve(q: str):
    token = os.environ.get("EODHD_API_KEY","")
    if not token:
        return {"ok": False, "error": "EODHD_API_KEY missing"}
    url = f"https://eodhd.com/api/search/{q}"
    r = requests.get(url, params={"api_token": token, "fmt":"json"}, timeout=20)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=r.text)
    return r.json()
