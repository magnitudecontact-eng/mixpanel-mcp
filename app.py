from fastapi import FastAPI, HTTPException
import os, uuid

app = FastAPI(title="Mixpanel MCP Bridge (stub)")

@app.get("/")
def root():
    return {"ok": True, "service": "mixpanel-mcp"}

@app.get("/health")
def health_alt():
    return {"ok": True}

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/tools/search")
async def tools_search(payload: dict):
    event = payload.get("event")
    allowed = os.getenv("ALLOWED_EVENTS", "")
    allowed_events = {e for e in allowed.split(",") if e} if allowed else None
    if allowed_events is not None and event not in allowed_events:
        raise HTTPException(status_code=404, detail="Unknown event")
    return {"id": str(uuid.uuid4()), "title": f"Search: {event}", "text": f"(stub) results for {event}"}

@app.post("/tools/fetch")
async def tools_fetch(payload: dict):
    return {"objects": payload.get("objectIds", [])}
