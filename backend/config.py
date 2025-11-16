import os
from dataclasses import dataclass
from typing import Optional

CACHE_DB_DEFAULT = "backend/results/cache.sqlite"

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
    cache_db: Optional[str] = os.environ.get("CACHE_DB")
    store_results: bool = os.environ.get("STORE_RESULTS", "true").lower() == "true"

CFG = Config()
if isinstance(CFG.cache_db, str):
    CFG.cache_db = CFG.cache_db.strip() or None
if CFG.cache_db is None and CFG.store_results:
    CFG.cache_db = CACHE_DB_DEFAULT
