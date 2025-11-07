import os, json
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
app=FastAPI()
orig=os.environ.get("ALLOWED_ORIGINS","*").split(",")
app.add_middleware(CORSMiddleware,allow_origins=[o.strip() for o in orig if o.strip()],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.get("/health")
def health(): return {"ok":True,"asof":datetime.now(timezone.utc).isoformat()}
def eod_search(q,t): 
    u=f"https://eodhd.com/api/search/{q}?api_token={t}&fmt=json"
    r=requests.get(u,timeout=12); r.raise_for_status(); return r.json()
@app.get("/v1/resolve")
def resolve(q:str, preferUS:int=1):
    t=os.environ.get("EODHD_API_KEY","").strip()
    if not t: return {"ok":False,"error":"missing_api_key","rows":[]}
    try:
        raw=eod_search(q,t); rows=[]
        for it in raw:
            code=it.get("Code") or it.get("code") or ""
            ex=it.get("Exchange") or it.get("exchange") or ""
            name=it.get("Name") or it.get("name") or ""
            score=it.get("Score") or it.get("score") or 0
            rows.append({"code":code,"exchange":ex,"name":name,"score":score})
        if preferUS: rows=sorted(rows,key=lambda x:(x["exchange"]!="US",-float(x["score"] or 0)))
        return {"ok":True,"rows":rows}
    except Exception as e: return {"ok":False,"error":"upstream","detail":str(e),"rows":[]}
