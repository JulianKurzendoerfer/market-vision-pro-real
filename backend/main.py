import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

allowed = os.getenv("ALLOWED_ORIGINS", "*").strip()
if allowed == "*" or allowed == "":
    origins = ["*"]
else:
    origins = [o.strip() for o in allowed.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/ping")
def ping():
    return {"pong": True}
