
import os, json, base64, hashlib, time
from datetime import date, timedelta
from typing import List, Dict, Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------- Config from env ----------
BASE = os.environ.get("MIXPANEL_BASE", "https://mixpanel.com/api").rstrip("/")
PID  = os.environ.get("MIXPANEL_PROJECT_ID", "").strip()
SAU  = os.environ.get("MIXPANEL_SA_USERNAME", "").strip()
SAS  = os.environ.get("MIXPANEL_SA_SECRET", "").strip()
ALLOWED = {e.strip() for e in os.environ.get("ALLOWED_EVENTS","").split(",") if e.strip()}
PORT = int(os.environ.get("PORT", "8080"))

if not (BASE and PID and SAU and SAS):
    print("[WARN] Missing one or more required env vars: MIXPANEL_BASE, MIXPANEL_PROJECT_ID, MIXPANEL_SA_USERNAME, MIXPANEL_SA_SECRET")

AUTH = "Basic " + base64.b64encode(f"{SAU}:{SAS}".encode()).decode()
HEADERS = {"Authorization": AUTH, "Accept": "application/json"}

# Simple in-memory cache (swap for Redis in prod)
CACHE: Dict[str, Dict[str, Any]] = {}
TTL_SECONDS = 15 * 60

def _today_str():
    return date.today().isoformat()

def _days_ago_str(n: int):
    return (date.today() - timedelta(days=n)).isoformat()

def _rid(spec: Dict[str,Any]) -> str:
    return "seg#" + hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()

async def _mxp_get(client, path, params):
    url = f"{BASE}{path}"
    params = {"project_id": PID, **params}
    r = await client.get(url, params=params, headers=HEADERS, timeout=45)
    if r.status_code == 429:
        raise HTTPException(429, detail="Mixpanel rate limit hit. Please retry shortly.")
    if r.status_code >= 400:
        raise HTTPException(r.status_code, detail=f"Mixpanel error: {r.text}")
    return r.json()

class SearchIn(BaseModel):
    query: str = ""
    event: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    unit: str = "day"
    breakdown: str | None = None      # e.g. properties["platform"]
    where: str | None = None
    top_k: int = 5

class SearchOutItem(BaseModel):
    id: str
    title: str
    text: str
    preview: Dict[str,Any] | None = None

class FetchIn(BaseModel):
    objectIds: List[str]

app = FastAPI(title="Mixpanel MCP")

@app.post("/tools/search", response_model=List[SearchOutItem])
async def mcp_search(inp: SearchIn):
    ev = (inp.event or "").strip()
    if not ev and " " not in inp.query:
        ev = inp.query.strip()
    if not ev:
        raise HTTPException(400, "Please specify an event, e.g. event=sign_up_success")

    if ALLOWED and ev not in ALLOWED:
        raise HTTPException(400, f"Unknown event '{ev}'. Allowed (sample): {sorted(ALLOWED)[:10]}")

    frm = inp.from_date or _days_ago_str(7)
    to  = inp.to_date or _today_str()
    unit = inp.unit or "day"
    on = inp.breakdown or 'properties["platform"]'

    params = {"event": ev, "from_date": frm, "to_date": to, "unit": unit, "on": on}
    if inp.where:
        params["where"] = inp.where

    spec = {"endpoint": "/query/segmentation", "params": params}
    rid = _rid(spec)

    now = time.time()
    if rid in CACHE and now - CACHE[rid]["ts"] < TTL_SECONDS:
        data = CACHE[rid]["data"]
    else:
        async with httpx.AsyncClient() as client:
            data = await _mxp_get(client, spec["endpoint"], spec["params"])
        CACHE[rid] = {"ts": now, "data": data, "spec": spec}

    groups = list((data.get("data") or {}).keys())
    top = groups[: max(1, min(inp.top_k, 5))]
    title = f"{ev} · {frm}→{to} · by {on.replace('properties[','').replace(']','')}"
    text = ", ".join(top) if top else "no data"
    return [SearchOutItem(id=rid, title=title, text=text, preview={"top": top, "series": data.get("series")})]

@app.post("/tools/fetch")
async def mcp_fetch(inp: FetchIn):
    out = {}
    async with httpx.AsyncClient() as client:
        for oid in inp.objectIds:
            cell = CACHE.get(oid)
            if not cell:
                out[oid] = {"error": "Expired or unknown id. Please re-run search."}
                continue
            spec = cell["spec"]
            data = await _mxp_get(client, spec["endpoint"], spec["params"])
            out[oid] = {"meta": {"endpoint": "segmentation", **spec["params"]}, "payload": data}
    return out

@app.get("/healthz")
def health():
    return {"ok": True}
