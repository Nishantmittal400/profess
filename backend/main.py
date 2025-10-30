from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, uuid, tempfile, time

from dotenv import load_dotenv
load_dotenv()
from backend.config import CFG
from backend.transcribe_openai import transcribe_audio_bytes
from backend.diarize_simple import (
    embed_segments,
    assign_speakers_k2,
    map_roles_by_talk_time,
    merge_contiguous_segments,
)
from backend.discourse_coach import label_transcript
from backend.metrics_engine import compute_all

app = FastAPI(title="Make Teaching Great Again – Local")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

os.makedirs(CFG.results_dir, exist_ok=True)

@app.get("/health")
def health():
    return {"ok": True, "use_llm": CFG.use_llm, "llm_model": CFG.llm_model, "transcriber": CFG.transcriber}

@app.post("/process")
async def process(audio: UploadFile = File(...)):
    if not CFG.openai_api_key:
        raise HTTPException(500, "OPENAI_API_KEY missing")
    if audio.content_type and not audio.content_type.startswith("audio/"):
        raise HTTPException(400, "Please upload an audio file.")

    raw = await audio.read()
    steps = {}

    # 1) Transcribe (OpenAI Whisper API)
    t0 = time.perf_counter()
    text, verbose = transcribe_audio_bytes(raw, filename=audio.filename or "audio.wav")
    segments = [{"start": float(s["start"]), "end": float(s["end"]), "text": s.get("text", ""),
                 "speaker": "", "role": "unknown"} for s in verbose.get("segments", [])]
    transcription_segments = [dict(seg) for seg in segments]
    if not segments:
        raise HTTPException(500, "No segments produced by Whisper.")
    transcription_duration = time.perf_counter() - t0
    steps["transcription"] = {
        "status": "completed",
        "duration_ms": int(transcription_duration * 1000),
        "text": text,
        "segment_count": len(transcription_segments),
        "segments": transcription_segments
    }

    # 2) Temp wav for diarization embeddings
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        tmp_path = f.name
        f.write(raw)

    # 3) Diarize simple (ECAPA + KMeans k=2) then map roles
    diarize_start = time.perf_counter()
    diarized_segments = []
    try:
        embs = embed_segments(tmp_path, segments)
        segments = assign_speakers_k2(segments, embs)
        segments = merge_contiguous_segments(segments)
        segments = map_roles_by_talk_time(segments)
        diarized_segments = [dict(s) for s in segments]
    finally:
        try: os.unlink(tmp_path)
        except: pass
    steps["diarization"] = {
        "status": "completed",
        "duration_ms": int((time.perf_counter() - diarize_start) * 1000),
        "segment_count": len(diarized_segments),
        "segments": diarized_segments,
    }

    # 4) Paragraph-level LLM discourse analysis (labels + coach)
    labeling_start = time.perf_counter()
    labeled, coach_report, coach_meta = label_transcript(segments)
    labeling_duration = time.perf_counter() - labeling_start
    steps["labeling"] = {
        "status": "completed",
        "duration_ms": int(labeling_duration * 1000),
        "utterance_count": len(labeled),
        "utterances": labeled,
        "meta": coach_meta,
    }

    # 5) Metrics & timeline
    metrics_start = time.perf_counter()
    metrics = compute_all(labeled, coach_report=coach_report)
    steps["metrics"] = {
        "status": "completed",
        "duration_ms": int((time.perf_counter() - metrics_start) * 1000),
        "metrics": metrics,
    }

    # 6) Coach analysis
    steps["coach_analysis"] = {
        "status": "completed",
        "duration_ms": 0,
        "report": coach_report,
        "meta": coach_meta,
    }

    # 7) Save and return
    sid = uuid.uuid4().hex[:8]
    out_dir = os.path.join(CFG.results_dir, sid)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "utterances.json"), "w", encoding="utf-8") as f:
        json.dump(labeled, f, ensure_ascii=False)
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False)
    with open(os.path.join(out_dir, "coach_report.json"), "w", encoding="utf-8") as f:
        json.dump(coach_report, f, ensure_ascii=False)

    return JSONResponse({
        "session_id": sid,
        "duration_sec": metrics.get("class_duration_sec", labeled[-1]["end"]),
        "steps": steps,
        "metrics": {k: v for k, v in metrics.items() if k != "timeline"},
        "timeline": metrics.get("timeline", []),
        "coach_report": coach_report,
    })
