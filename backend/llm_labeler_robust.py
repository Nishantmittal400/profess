# backend/llm_labeler_robust.py
import json, time
from typing import Dict, List, Literal
from openai import OpenAI
from backend.cache import SQLiteCache
from backend.config import CFG

# NEW
from string import Template
from pydantic import BaseModel, Field, ValidationError

client = OpenAI(api_key=CFG.openai_api_key)
cache = SQLiteCache(CFG.cache_db)

SYSTEM = (
    "You are a discourse analyst for classroom interactions using the OHCR framework.\n"
    "Evaluate the target utterance in its conversational context.\n"
    "Return OHCR='O','H','C','R' only when the utterance clearly performs that move; otherwise set OHCR='None'.\n"
    "Definitions: O=observe (describe evidence), H=hypothesize (propose explanation), "
    "C=challenge (question/contest), R=resolve (synthesize/conclude).\n"
    "Also return discourse_act: question|statement|regulatory|other; role: teacher|student|unknown; "
    "confidence 0..1; rationale <=30 words."
)

# NEW: Template so JSON braces don't conflict
PROMPT = Template(
    "Context_before: $before\n"
    "Target: $target\n"
    "Context_after: $after\n"
    "Return strict JSON: {\n"
    '  "ohcr": "O|H|C|R|None",\n'
    '  "discourse_act": "question|statement|regulatory|other",\n'
    '  "role": "teacher|student|unknown",\n'
    '  "confidence": 0.0,\n'
    '  "rationale": ""\n'
    "}\n"
)
# ---- Quality schema & coercion ----
class LLMLabel(BaseModel):
    ohcr: Literal["O", "H", "C", "R", "None"]
    discourse_act: Literal["question", "statement", "regulatory", "other"]
    role: Literal["teacher", "student", "unknown"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str

ALLOWED_OHCR = {"O","H","C","R","None"}
ALLOWED_ACT  = {"question","statement","regulatory","other"}
ALLOWED_ROLE = {"teacher","student","unknown"}

def _normalize_payload(data: Dict) -> Dict:
    # defensive normalization
    d = dict(data or {})
    d["ohcr"] = str(d.get("ohcr","None")).strip().upper()
    if d["ohcr"] not in ALLOWED_OHCR: d["ohcr"] = "None"

    act = str(d.get("discourse_act","other")).strip().lower()
    d["discourse_act"] = act if act in ALLOWED_ACT else "other"

    role = str(d.get("role","unknown")).strip().lower()
    d["role"] = role if role in ALLOWED_ROLE else "unknown"

    try:
        d["confidence"] = float(d.get("confidence", 0.0))
    except Exception:
        d["confidence"] = 0.0
    d["confidence"] = max(0.0, min(1.0, d["confidence"]))

    d["rationale"] = str(d.get("rationale",""))[:200]  # keep concise
    return d

def label_one(before: List[Dict], target: Dict, after: List[Dict]) -> Dict:
    payload = {
        "v": "v2.1",  # bump to invalidate old cache if needed
        "model": CFG.llm_model,
        "before": before,
        "target": target,
        "after": after
    }

    def _compute():
        # --- build message safely with Template ---
        try:
            msg = PROMPT.substitute(
                before=json.dumps(before, ensure_ascii=False),
                target=json.dumps(target, ensure_ascii=False),
                after=json.dumps(after, ensure_ascii=False),
            )
        except KeyError as e:
            # Very explicit error if a variable name is wrong
            raise RuntimeError(f"Prompt variable missing: {e}") from e

        last_err = None
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=CFG.llm_model,
                    temperature=0,               # deterministic
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": msg}
                    ],
                    response_format={"type": "json_object"},
                    timeout=30,                  # keep tight
                )
                content = resp.choices[0].message.content
                raw = json.loads(content)

                # normalize + validate
                norm = _normalize_payload(raw)
                obj = LLMLabel(**norm)
                meta = {
                    "ptoks": getattr(resp.usage, "prompt_tokens", None),
                    "ctoks": getattr(resp.usage, "completion_tokens", None),
                }
                return obj.model_dump(), meta

            except (json.JSONDecodeError, ValidationError) as e:
                last_err = e
            except Exception as e:
                last_err = e
                time.sleep(0.8 * (attempt + 1))  # backoff

        # If all attempts fail, return a safe default
        # (hybrid will still compare confidence/role)
        return {"ohcr": "None", "discourse_act": "other",
                "role": "unknown", "confidence": 0.0, "rationale": ""}, {}

    out, _ = cache.get_or_set(payload, _compute)
    return {
        "ohcr": out.get("ohcr", "None"),
        "discourse_act": out.get("discourse_act", "other"),
        "role": out.get("role", "unknown"),
        "confidence": float(out.get("confidence", 0.0)),
        "rationale": out.get("rationale", ""),
        "source": "llm"
    }

def hybrid_label(utterances: List[Dict]) -> List[Dict]:
    labeled = []
    for i, u in enumerate(utterances):
        before = utterances[max(0, i-2):i]
        after  = utterances[i+1:i+2]

        if not CFG.use_llm:
            labeled.append({
                **u,
                "ohcr": "None",
                "discourse_act": "statement" if "?" not in u["text"] else "question",
                "role": u.get("role", "unknown"),
                "confidence": 0.0,
                "rationale": "LLM disabled"
            })
            continue

        llm_pred = label_one(before, u, after)
        final_pred = {**u, **llm_pred}

        if final_pred.get("role", "unknown") == "unknown":
            final_pred["role"] = u.get("role", "unknown")

        if final_pred.get("confidence", 0.0) < CFG.conf_threshold:
            final_pred["ohcr"] = "None"

        final_pred.setdefault("source", "llm")
        labeled.append(final_pred)
    return labeled
