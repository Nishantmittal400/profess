FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps required by librosa/soundfile + ffmpeg for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    libsndfile1 \
    git \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY pretrained_models ./pretrained_models

# Ensure results + cache directories exist at runtime
RUN mkdir -p backend/results && mkdir -p backend/results/cache

ENV RESULTS_DIR=/app/backend/results \
    CACHE_DB=/app/backend/results/cache.sqlite \
    SB_CACHE_DIR=/app/.sb_cache

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
