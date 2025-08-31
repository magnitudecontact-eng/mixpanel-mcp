
# Mixpanel → ChatGPT MCP Connector (Cloud Run)

This is a no-frills bridge that lets ChatGPT query your Mixpanel project live.

## What it exposes
- `POST /tools/search`  — summarize a segmentation query
- `POST /tools/fetch`   — return the full Mixpanel JSON for a prior search
- `GET  /healthz`       — health check

## Environment variables
- `MIXPANEL_BASE` — `https://mixpanel.com/api` or `https://eu.mixpanel.com/api` or `https://in.mixpanel.com/api`
- `MIXPANEL_PROJECT_ID` — your Mixpanel project id (number)
- `MIXPANEL_SA_USERNAME` — service account username
- `MIXPANEL_SA_SECRET` — service account secret
- `ALLOWED_EVENTS` — optional CSV whitelist (recommended)

## Local run (optional)
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat sample.env | xargs) && uvicorn app:app --host 0.0.0.0 --port 8080
```

## Cloud Run (one-time)
```
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

REGION=us-central1
REPO=mcp-bridge
IMAGE=${REGION}-docker.pkg.dev/$(gcloud config get-value project)/$REPO/mixpanel-mcp:1

gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION --description="MCP images" || true

gcloud builds submit --tag $IMAGE .

gcloud run deploy mixpanel-mcp   --image $IMAGE   --region $REGION   --platform managed   --allow-unauthenticated   --min-instances=0   --set-env-vars MIXPANEL_BASE=https://mixpanel.com/api   --set-env-vars MIXPANEL_PROJECT_ID=YOUR_PROJECT_ID   --set-env-vars MIXPANEL_SA_USERNAME=YOUR_SERVICE_ACCOUNT_USERNAME   --set-env-vars MIXPANEL_SA_SECRET=YOUR_SERVICE_ACCOUNT_SECRET   --set-env-vars ALLOWED_EVENTS=sign_up_success,listing_viewed,job_matcher_attempt,search_initiated
```

After deploy, note the service URL:
- `https://mixpanel-mcp-xxxxx-uc.a.run.app`

## Testing
- Health: `GET /healthz`
- Search:
```
POST /tools/search
{"event":"sign_up_success","from_date":"2025-08-24","to_date":"2025-08-31","unit":"day","breakdown":"properties[\"platform\"]"}
```
- Fetch the returned `id`:
```
POST /tools/fetch
{"objectIds":["<id from search>"]}
```

## Add to ChatGPT
Settings → Connectors → Add → Custom Connector (MCP) → paste your Cloud Run URL.
