FROM python:3.11-slim

WORKDIR /app

# Install only what's needed, no cache to keep image small
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway injects $PORT, default to 8000 for local testing
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
