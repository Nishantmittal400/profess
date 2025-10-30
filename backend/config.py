import os
from dataclasses import dataclass

@dataclass
class Config:
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    transcriber: str = os.environ.get("TRANSCRIBER", "openai")
    llm_model: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    use_llm: bool = os.environ.get("USE_LLM", "true").lower() == "true"
    conf_threshold: float = float(os.environ.get("CONF_THRESHOLD", 0.5))
    diarizer: str = os.environ.get("DIARIZER", "simple")
    max_speakers: int = int(os.environ.get("MAX_SPEAKERS", 2))
    results_dir: str = os.environ.get("RESULTS_DIR", "backend/results")
    cache_db: str = os.environ.get("CACHE_DB", "backend/results/cache.sqlite")

CFG = Config()
