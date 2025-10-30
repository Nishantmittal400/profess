from openai import OpenAI
import io, os
from typing import Tuple, Dict, Any

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.wav") -> Tuple[str, Dict[str, Any]]:
    f = io.BytesIO(audio_bytes); f.name = filename
    resp = client.audio.transcriptions.create(
        model="whisper-1",
        file=f,
        response_format="verbose_json",
        temperature=0
    )
    data = resp.model_dump() if hasattr(resp, "model_dump") else resp
    return (data.get("text", ""), data)
