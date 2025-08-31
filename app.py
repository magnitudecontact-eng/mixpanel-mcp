from fastapi import FastAPI, HTTPException
import os, uuid

app = FastAPI(title="Mixpanel MCP Bridge (stub)")

_allowed = os.getenv("ALLOWED_EVENTS", "")
ALLOWED_EVENTS = set([e for e in _allowed.split(",") if e]) if _allowed else None

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/tools/search")
async def tools_search(payload: dict):
    event = payload.get("event")
    if ALLOWED_EVENTS is not None and event not in ALLOWED_EVENTS:
        raise HTTPException(status_code=404, detail="Unknown event")
    return {"id": str(uuid.uuid4()), "title": f"Search: {event}", "text": f"(stub) results for {event}"}

@app.post("/tools/fetch")
async def tools_fetch(payload: dict):
    return {"objects": payload.get("objectIds", [])}
