
# Python slim image
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py ./

# Health check (optional)
HEALTHCHECK CMD curl -f http://localhost:${PORT:-8080}/healthz || exit 1

# Run
ENV PORT=8080
CMD ["bash", "-lc", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
