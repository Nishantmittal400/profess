# Profess

OHCR discourse analytics stack consisting of a FastAPI backend for transcription/analysis and a Vite + React + Tailwind frontend for visualization.

## Stack overview
- **Backend**: FastAPI + Uvicorn, Whisper transcription via OpenAI, diarization (SpeechBrain ECAPA + scikit-learn), metrics, tiered LLM prompts. Depends on Python 3.11+ and system audio libs (`ffmpeg`, `libsndfile`).
- **Frontend**: Vite + React + Tailwind. Uses `wavesurfer.js` for waveform preview and `recharts` for charts. Communicates with the backend via a configurable API base URL.

---

## 1. Requirements
- Python 3.11+
- Node.js 18+ / npm 9+
- An OpenAI API key with Whisper + Responses access
- ffmpeg + libsndfile installed on hosts that will run the backend

Optional but recommended: Docker + Docker Compose v2 for containerized deployments.

---

## 2. Environment configuration
Copy the template and fill in credentials:

```bash
cp .env.example .env
```

Required entries:

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY` | API key used by Whisper + LLM analysis |
| `LLM_MODEL` | OpenAI Responses model (defaults to `gpt-4o-mini`) |
| `RESULTS_DIR`, `CACHE_DB` | Where transcripts + cache will be written (leave `CACHE_DB` blank to disable caching) |
| `STORE_RESULTS` | Set to `false` to skip writing transcripts/metrics to disk |
| `VITE_API_BASE` | Backend URL baked into the Vite build (`http://127.0.0.1:8000` for local dev) |

All backend settings are read in `backend/config.py`. `load_dotenv()` is called automatically on startup.

---

## 3. Local development

### Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
The API exposes `/health` and `/process`. Transcription/LLM calls require `OPENAI_API_KEY`.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Vite serves the UI at `http://localhost:5173` and proxies requests to the backend specified in `VITE_API_BASE`. In development you can also override the target at runtime via `window.__APP_CONFIG__ = { apiBase: "http://your-host" };` before the app mounts.

---

## 4. Deployment

### Docker Compose (recommended)
Build both services and run them together:
```bash
cp .env.example .env    # ensure OPENAI_API_KEY + VITE_API_BASE set
docker compose build
docker compose up
```
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:4173` (served by nginx)

Compose mounts named volumes for `backend/results` and the SpeechBrain cache so transcripts persist across restarts.

### Render backend + Vercel frontend
The repo now includes `render.yaml` and `vercel.json` for this split-stack deployment:

1. **Render**
   - Create a new *Blueprint* and point Render to this repo. The blueprint uses `backend.Dockerfile`, so Render builds the same container you run locally (with ffmpeg/libsndfile baked in).
   - After the first deploy, open the service settings and add environment variables (`OPENAI_API_KEY`, `LLM_MODEL`, etc.). The blueprint marks `OPENAI_API_KEY` as `sync: false`, so you set it directly in Render.
   - `STORE_RESULTS` defaults to `false` so no transcripts/results are persisted on the container filesystem; remove or change it if you prefer persistence.
   - Attach a persistent disk if you need to keep files in `/app/backend/results` across deploys.
2. **Vercel**
   - Import the repo and leave “Root Directory” empty. `vercel.json` tells Vercel to `cd frontend && npm run build` and serve `frontend/dist`.
   - In Vercel Project → Settings → Environment Variables, add `VITE_API_BASE=https://<your-render-service>.onrender.com`.
   - Trigger a redeploy; the static assets will be served via Vercel’s CDN while API traffic flows to Render.

### Manual deployment
1. Provision a host with Python 3.11+, ffmpeg, libsndfile, and Node 18+.
2. Install backend dependencies (`pip install -r requirements.txt`) and keep `pretrained_models` accessible (already checked in to avoid first-run downloads).
3. Start the API with `uvicorn backend.main:app --host 0.0.0.0 --port 8000`. A `Procfile` is included for platforms like Heroku/Render (`web: uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}`).
4. Build the frontend with:
   ```bash
   cd frontend
   VITE_API_BASE="https://your-backend-host" npm run build
   ```
   Serve `frontend/dist` with any static host (nginx, CDN, object storage).

---

## 5. Useful notes
- First-time diarization downloads from Hugging Face can be slow; bundling `pretrained_models/EncoderClassifier-*` avoids re-downloading in production.
- Backend writes transcripts, metrics, and tier analyses into `backend/results/<session-id>`. Mount/persist this directory if you deploy to containers.
- Frontend fallbacks: if you need to change the backend URL without rebuilding, define `window.__APP_CONFIG__ = { apiBase: "https://new-backend" };` before loading `index.html`.

## 6. Privacy & secrets
- Set `STORE_RESULTS=false` (default in `.env.example`) to keep the backend stateless; no transcripts, metrics, or cache files are persisted.
- When `STORE_RESULTS=false`, caching is also disabled so no derived data lands on disk.
- Never expose `OPENAI_API_KEY` (or other sensitive values) to the frontend. Only `VITE_API_BASE` is passed to the Vite build; everything else stays server-side via Render/Vercel environment variables.
- Rotate API keys in Render’s secret manager if they might have been exposed, and limit access to the deployment dashboards.

This repository is now ready for container-based deployments as well as traditional VM setups. Reach out via issues for questions or enhancements.
