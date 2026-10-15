# RuleRadar AI - Production Dockerfile
# Self-contained, zero cloud API dependencies, persistent local volume for zero data loss

FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    DATA_DIR=/app/data \
    HF_HOME=/app/cache/huggingface \
    TORCH_HOME=/app/cache/torch

WORKDIR /app

# Install minimal OS dependencies for PyMuPDF and healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pre-create cache and data directories with open permissions
RUN mkdir -p /app/cache /app/data && chmod -R 777 /app/cache /app/data

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download SpaCy model and Hugging Face embedding model into fixed cache during build
# This guarantees 100% offline runtime with zero cold-start download delay under any user UID
RUN python -m spacy download en_core_web_sm && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" && \
    chmod -R 777 /app/cache

# Copy application source code
COPY app/ ./app/

# Declare persistent volume mount point for SQLite database and uploaded files
# Ensure zero data loss across container restarts or redeployments
VOLUME ["/app/data"]

EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/api/system/health || exit 1

# Start Uvicorn production server reading dynamic PORT if provided by cloud host
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
