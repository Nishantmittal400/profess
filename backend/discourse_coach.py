import json
import time
from typing import Dict, List, Tuple

from openai import OpenAI

from backend.cache import SQLiteCache
from backend.config import CFG

client = OpenAI(api_key=CFG.openai_api_key)
cache = SQLiteCache(CFG.cache_db)

COACH_SYSTEM_PROMPT = """You are an OHCR discourse analyst and teaching coach.

TASKS
1) Group consecutive utterances into DISCOURSE MOVES (one intent per move).
2) For each move, assign a single DISCOURSE ACT: question | statement | regulatory.
3) Map moves to OHCR: O | H | C | R | none.
   - O (Observe) = factual, non-interpretive presentation of a phenomenon/data to notice. Open-ended discussion encouraging questions asked by teacher. Teacher giving alternate statements urging students to think further.
   - H (Hypothesize) = proposed explanation for the phenomenon/knowledge problem / discussion encouraging questions. Usually answers provided by students but could also be by teacher.
   - C (Challenge) = question/critique exposing gaps, counterexamples, or limits. Usually questions/doubts asked by students but could be by teacher also.
   - R (Resolve) = synthesis/closure that integrates/clarifies and has teacher agreement.
4) Identify if a strict **Knowledge Question** is present (a conceptual puzzle emerging from O; not recall/procedural).
5) Provide brief coach_notes for each move (clarity, sequencing, scaffolding).
6) Classify each move into the Interaction Analysis Model (IAM) phase 1-5 (Gunawardena et al. 1997; Lucas et al. 2014):
   - 1 = Sharing/Comparing of Information (“I think…”, “According to…”, “In my experience…”)
   - 2 = Discovery/Exploration of Dissonance (“I disagree because…”, “But what about…”, “There seems to be a contradiction…”)
   - 3 = Negotiation of Meaning / Co-construction (“Let’s clarify…”, “So what you’re saying is…”, “Maybe we can combine our ideas…”)
   - 4 = Testing and Modification of Proposed Synthesis (“Let’s try applying…”, “What if we assume…”, “Does this hold true for…?”)
   - 5 = Agreement / Application of Newly Constructed Meaning (“We all agree that…”, “This can be used to…”, “Based on our discussion we conclude…”)
   Provide an `iam_level` integer 1–5 and concise `iam_rationale` citing the language that justifies the phase.
7) List the distinct sub-topics or concepts discussed during the session (phrased as concise nouns/short phrases).
8) In the global_feedback block, deliver expanded, prescriptive pedagogical recommendations titled “Suggestions to Improve Teaching.” Focus on raising OHCR counts—especially encouraging spontaneous observing, questioning, and challenging. Offer concrete questioning stems, challenge prompts, or facilitation moves the teacher can try immediately.

STRICTNESS
- Do NOT mark O if no phenomenon/data was presented for noticing.
- A recall like “What is metric scale?” ≠ Knowledge Question (unless it arises from prior O).
- Prefer fewer, larger moves over per-sentence acts if intent is continuous.

OUTPUT must follow the JSON schema exactly. """

JSON_SCHEMA = {
    "name": "ohcr_discourse_analysis",
    "schema": {
        "type": "object",
        "properties": {
            "transcript_meta": {
                "type": "object",
                "properties": {
                    "num_turns": {"type": "integer"},
                    "has_observe": {"type": "boolean"},
                    "has_knowledge_question": {"type": "boolean"},
                },
                "required": ["num_turns", "has_observe", "has_knowledge_question"],
            },
            "moves": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "move_id": {"type": "string"},
                        "turn_range": {"type": "string"},
                        "speakers": {"type": "array", "items": {"type": "string"}},
                        "utterance_summary": {"type": "string"},
                        "discourse_act": {
                            "type": "string",
                            "enum": ["question", "statement", "regulatory"],
                        },
                        "ohcr": {"type": "string", "enum": ["O", "H", "C", "R", "none"]},
                        "coach_notes": {"type": "string"},
                        "iam_level": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5
                        },
                        "iam_rationale": {"type": "string"},
                    },
                    "required": [
                        "move_id",
                        "turn_range",
                        "speakers",
                        "utterance_summary",
                        "discourse_act",
                        "ohcr",
                        "coach_notes",
                        "iam_level",
                        "iam_rationale",
                    ],
                },
            },
            "global_feedback": {
                "type": "object",
                "properties": {
                    "diagnosis": {"type": "string"},
                    "improvements": {"type": "array", "items": {"type": "string"}},
                    "next_time_observe_script": {"type": "string"},
                    "rubric_flags": {
                        "type": "object",
                        "properties": {
                            "observe_is_factual": {"type": "boolean"},
                            "observe_sets_problem": {"type": "boolean"},
                            "kq_is_conceptual_not_recall": {"type": "boolean"},
                            "sequencing_supports_inquiry": {"type": "boolean"},
                        },
                        "required": [
                            "observe_is_factual",
                            "observe_sets_problem",
                            "kq_is_conceptual_not_recall",
                            "sequencing_supports_inquiry",
                        ],
                    },
                },
                "required": [
                    "diagnosis",
                    "improvements",
                    "next_time_observe_script",
                    "rubric_flags",
                ],
            },
            "topics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Distinct sub-topics or concepts mentioned during the session."
            },
        },
        "required": ["transcript_meta", "moves", "global_feedback", "topics"],
        "additionalProperties": False,
    },
    "strict": True,
}

_DEFAULT_REPORT = {
    "transcript_meta": {"num_turns": 0, "has_observe": False, "has_knowledge_question": False},
    "moves": [],
    "global_feedback": {
        "diagnosis": "No transcript available for analysis.",
        "improvements": [
            "Provide a recording or transcript with clear teacher and student turns.",
        ],
        "next_time_observe_script": "",
        "rubric_flags": {
            "observe_is_factual": False,
            "observe_sets_problem": False,
            "kq_is_conceptual_not_recall": False,
            "sequencing_supports_inquiry": False,
        },
    },
    "topics": [],
}


def _default_report() -> Dict:
    return json.loads(json.dumps(_DEFAULT_REPORT))


def _format_transcript(utterances: List[Dict]) -> List[Dict]:
    formatted = []
    for idx, utt in enumerate(utterances, start=1):
        speaker = utt.get("speaker", "")
        role = str(utt.get("role", "unknown")).strip().lower()
        if not speaker and role and role != "unknown":
            speaker = role.title()
        entry = {
            "turn": idx,
            "speaker": speaker,
            "text": (utt.get("text") or "").strip(),
        }
        if role:
            entry["role"] = role
        if "start" in utt:
            entry["start_s"] = float(utt["start"])
        if "end" in utt:
            entry["end_s"] = float(utt["end"])
        formatted.append(entry)
    return formatted


def _call_via_responses(transcript: List[Dict]) -> Tuple[Dict, Dict]:
    response = client.responses.create(
        model=CFG.llm_model,
        temperature=0.1,
        top_p=0.9,
        seed=7,
        system=COACH_SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": json.dumps({"transcript": transcript}, ensure_ascii=False)}
                ],
            }
        ],
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        timeout=60,
    )
    output = response.output[0].content[0].text
    parsed = json.loads(output)
    usage = getattr(response, "usage", None)
    meta: Dict = {}
    if usage is not None:
        meta = {
            "ptoks": getattr(usage, "prompt_tokens", None),
            "ctoks": getattr(usage, "completion_tokens", None),
        }
    return parsed, meta


def _call_via_chat(transcript: List[Dict]) -> Tuple[Dict, Dict]:
    schema_hint = json.dumps(JSON_SCHEMA["schema"], ensure_ascii=False)
    payload = json.dumps({"transcript": transcript}, ensure_ascii=False)
    resp = client.chat.completions.create(
        model=CFG.llm_model,
        temperature=0.1,
        top_p=0.9,
        seed=7,
        messages=[
            {"role": "system", "content": COACH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Return a JSON object that strictly matches the following JSON schema: "
                    f"{schema_hint}\n"
                    f"Transcript payload:\n{payload}"
                ),
            },
        ],
        response_format={"type": "json_object"},
        timeout=60,
    )
    content = resp.choices[0].message.content
    parsed = json.loads(content)
    usage = getattr(resp, "usage", None)
    meta: Dict = {}
    if usage is not None:
        meta = {
            "ptoks": getattr(usage, "prompt_tokens", None),
            "ctoks": getattr(usage, "completion_tokens", None),
        }
    return parsed, meta


def _run_coach(transcript: List[Dict]) -> Tuple[Dict, Dict]:
    if not transcript:
        report = _default_report()
        report["transcript_meta"]["num_turns"] = 0
        return report, {"source": "fallback", "reason": "empty_transcript"}

    if not CFG.use_llm or not CFG.openai_api_key:
        report = _default_report()
        report["transcript_meta"]["num_turns"] = len(transcript)
        return report, {"source": "fallback", "reason": "llm_disabled_or_missing_key"}

    payload = {
        "v": "coach_v4",
        "model": CFG.llm_model,
        "transcript": transcript,
    }

    def _compute():
        last_err = None
        for attempt in range(3):
            try:
                if getattr(client, "responses", None):
                    parsed, meta = _call_via_responses(transcript)
                else:
                    parsed, meta = _call_via_chat(transcript)
                meta.setdefault("source", "llm")
                return parsed, meta
            except Exception as err:
                last_err = err
                time.sleep(0.8 * (attempt + 1))

        fallback = _default_report()
        fallback["transcript_meta"]["num_turns"] = len(transcript)
        return fallback, {"source": "fallback", "error": str(last_err) if last_err else "unknown"}

    report, meta = cache.get_or_set(payload, _compute)
    if not isinstance(report, dict):
        fallback = _default_report()
        fallback["transcript_meta"]["num_turns"] = len(transcript)
        return fallback, {"source": "fallback", "error": "invalid_report"}
    meta.setdefault("source", "llm" if CFG.use_llm else "fallback")
    return report, meta


def coach_analysis(utterances: List[Dict]) -> Dict:
    transcript = _format_transcript(utterances)
    report, meta = _run_coach(transcript)
    copy_report = json.loads(json.dumps(report))
    copy_report.setdefault("_meta", {}).update(meta)
    return copy_report


def _turns_from_range(value: str) -> List[int]:
    if not value:
        return []
    value = value.strip()
    if "-" in value:
        start_str, end_str = value.split("-", 1)
        try:
            start = int(start_str)
            end = int(end_str)
        except ValueError:
            return []
        if end < start:
            start, end = end, start
        return list(range(start, end + 1))
    try:
        return [int(value)]
    except ValueError:
        return []


def _normalize_ohcr(value: str) -> str:
    if not value:
        return "None"
    label = str(value).strip().upper()
    if label in {"O", "H", "C", "R"}:
        return label
    if label == "NONE":
        return "None"
    return "None"


def label_transcript(utterances: List[Dict]) -> Tuple[List[Dict], Dict, Dict]:
    transcript = _format_transcript(utterances)
    report, meta = _run_coach(transcript)

    report_copy = json.loads(json.dumps(report))
    report_copy.setdefault("_meta", {}).update(meta)

    source_tag = "coach_llm" if meta.get("source") == "llm" else "coach_fallback"
    labeled: List[Dict] = []
    turn_lookup: Dict[int, Dict] = {}

    for formatted, original in zip(transcript, utterances):
        text = (original.get("text") or formatted.get("text") or "").strip()
        entry = {
            "turn": formatted["turn"],
            "start": float(original.get("start", formatted.get("start_s", 0.0))),
            "end": float(original.get("end", formatted.get("end_s", 0.0))),
            "speaker": original.get("speaker", formatted.get("speaker", "")),
            "role": str(original.get("role", formatted.get("role", "unknown"))).lower(),
            "text": text,
            "ohcr": "None",
            "discourse_act": "question" if "?" in text else "statement",
            "confidence": 0.1,
            "coach_notes": "",
            "coach_move_id": "",
            "source": source_tag,
            "iam_level": 1,
            "iam_rationale": "",
        }
        labeled.append(entry)
        turn_lookup[formatted["turn"]] = entry

    moves = report.get("moves") if isinstance(report, dict) else None
    if isinstance(moves, list):
        for idx, move in enumerate(moves, start=1):
            ohcr = _normalize_ohcr(move.get("ohcr", "none"))
            discourse_act = move.get("discourse_act", "statement")
            coach_notes = move.get("coach_notes", "")
            move_id = move.get("move_id") or f"M{idx}"
            turns = _turns_from_range(move.get("turn_range", ""))
            iam_level = move.get("iam_level")
            try:
                iam_level = int(iam_level)
            except (TypeError, ValueError):
                iam_level = None
            if iam_level is not None:
                iam_level = min(5, max(1, iam_level))
            iam_rationale = move.get("iam_rationale", "")
            for turn in turns:
                entry = turn_lookup.get(turn)
                if not entry:
                    continue
                entry["ohcr"] = ohcr
                entry["discourse_act"] = discourse_act
                entry["confidence"] = 0.9 if ohcr != "None" else 0.6
                entry["coach_notes"] = coach_notes
                entry["coach_move_id"] = move_id
                entry["source"] = "coach_llm"
                if iam_level is not None:
                    entry["iam_level"] = iam_level
                    entry["iam_rationale"] = iam_rationale

    return labeled, report_copy, meta
