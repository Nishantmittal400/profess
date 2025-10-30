# backend/diarize_simple.py
from typing import List, Dict
import os
import numpy as np
import librosa
import torch
from sklearn.cluster import KMeans
from speechbrain.pretrained import EncoderClassifier

# ---------- Cache the classifier once (no re-init per request) ----------
_SB_CACHE = os.environ.get("SB_CACHE_DIR", "./.sb_cache")
CLF = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir=_SB_CACHE,
    run_opts={"device": "cpu"}  # change to "cuda" if GPU available
)

# ---------- Embedding ----------
def embed_segments(audio_path: str, segments: List[Dict], sr: int = 16000) -> np.ndarray:
    """
    Load audio, slice by (start, end) in seconds, and return an embedding per segment.

    segments: list of dicts with keys {"start": float, "end": float}
    returns: np.ndarray with shape [num_segments, emb_dim]
    """
    # Load mono float32
    y, sr = librosa.load(audio_path, sr=sr, mono=True)

    embs = []
    min_dur = int(0.30 * sr)  # pad up to 300ms if too short

    with torch.no_grad():
        for seg in segments:
            s = max(0, int(seg["start"] * sr))
            e = min(len(y), int(seg["end"] * sr))
            chunk = y[s:e]

            # Handle empty segments
            if chunk.size == 0:
                # ECAPA-Voxceleb default embedding dim is 192
                embs.append(np.zeros((192,), dtype=np.float32))
                continue

            # Pad very short segments
            if chunk.size < min_dur:
                chunk = np.pad(chunk, (0, min_dur - chunk.size), mode="constant")

            # NumPy -> Torch [B=1, T] float32
            wav = torch.from_numpy(np.ascontiguousarray(chunk)).float().unsqueeze(0)
            wav_lens = torch.tensor([1.0])

            # Some versions accept wav_lens; try with it, then without
            try:
                emb = CLF.encode_batch(wav, wav_lens=wav_lens)
            except TypeError:
                emb = CLF.encode_batch(wav)

            emb = emb.squeeze().detach().cpu().numpy().astype(np.float32)
            embs.append(emb)

    return np.vstack(embs) if embs else np.zeros((0, 192), dtype=np.float32)

# ---------- Clustering to assign speakers ----------
def assign_speakers_k2(segments: List[Dict], embs: np.ndarray) -> List[Dict]:
    """
    K-means into 2 speakers: SPEAKER_0 / SPEAKER_1
    """
    kmeans = KMeans(n_clusters=2, random_state=0, n_init=10)
    labels = kmeans.fit_predict(embs)
    for seg, lab in zip(segments, labels):
        seg["speaker"] = f"SPEAKER_{int(lab)}"
    return segments

# ---------- Map roles (teacher vs student) by talk-time ----------
def map_roles_by_talk_time(segments: List[Dict]) -> List[Dict]:
    """
    Assign 'teacher' to the speaker with the most total duration; others become 'student'.
    """
    dur = {}
    for s in segments:
        sp = s.get("speaker", "SPEAKER_0")
        dur[sp] = dur.get(sp, 0.0) + (s["end"] - s["start"])
    teacher = max(dur, key=dur.get) if dur else "SPEAKER_0"
    for s in segments:
        s["role"] = "teacher" if s.get("speaker") == teacher else "student"
    return segments


def merge_contiguous_segments(segments: List[Dict], *, max_gap: float = 0.35) -> List[Dict]:
    """
    Merge consecutive segments so that diarization works at a paragraph level rather than sentence level.

    Segments merge when:
      - they originate from the same speaker label
      - the gap between the previous end and next start is <= max_gap seconds
    """
    if not segments:
        return []

    merged: List[Dict] = []
    current = dict(segments[0])
    for seg in segments[1:]:
        same_speaker = seg.get("speaker") == current.get("speaker")
        same_role = seg.get("role") == current.get("role")
        gap = max(0.0, float(seg["start"]) - float(current["end"]))

        if same_speaker and same_role and gap <= max_gap:
            current["end"] = float(seg["end"])
            text_a = (current.get("text") or "").rstrip()
            text_b = (seg.get("text") or "").lstrip()
            current["text"] = f"{text_a} {text_b}".strip()
        else:
            merged.append(current)
            current = dict(seg)
    merged.append(current)
    return merged
