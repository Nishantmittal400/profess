from bisect import bisect_left
from typing import Dict, List

STAGE_ORDER = ["O", "H", "C", "R"]
STAGE_INDEX = {stage: idx for idx, stage in enumerate(STAGE_ORDER)}
VALID_OHCR = set(STAGE_ORDER)


def _normalize_ohcr(value) -> str:
    if value is None:
        return "None"
    label = str(value).strip().upper()
    if label in VALID_OHCR:
        return label
    if label == "NONE":
        return "None"
    return "None"

def _extract_iam_level(value) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError):
        return None
    if 1 <= level <= 5:
        return level
    return None


def _simplify_utterance(u: Dict, index: int) -> Dict:
    return {
        "index": index,
        "start": float(u.get("start", 0.0)),
        "end": float(u.get("end", 0.0)),
        "speaker": str(u.get("speaker", "")),
        "role": str(u.get("role", "unknown")).lower(),
        "ohcr": _normalize_ohcr(u.get("ohcr", "None")),
        "discourse_act": u.get("discourse_act", ""),
        "confidence": float(u.get("confidence", 0.0)),
        "text": u.get("text", ""),
        "duration": max(0.0, float(u.get("end", 0.0)) - float(u.get("start", 0.0))),
        "iam_level": _extract_iam_level(u.get("iam_level")),
    }

def _finalize_episode(episodes: List[Dict], current: Dict) -> None:
    if not current or not current.get("moves"):
        return
    moves = current["moves"]
    counts = {stage: 0 for stage in STAGE_ORDER}
    confidences = []
    teacher_moves = 0
    student_moves = 0

    for mv in moves:
        counts[mv["ohcr"]] = counts.get(mv["ohcr"], 0) + 1
        confidences.append(mv.get("confidence", 0.0))
        if mv.get("role") == "teacher":
            teacher_moves += 1
        elif mv.get("role") == "student":
            student_moves += 1

    coverage = sum(1 for stage in STAGE_ORDER if counts.get(stage, 0) > 0) / len(STAGE_ORDER)
    avg_conf = (sum(confidences) / len(confidences)) if confidences else 0.0
    flow_penalty = current["order_violations"] + current["skipped_stages"]
    denom = max(len(moves) - 1, 1)
    flow_score = max(0.0, 1.0 - (flow_penalty / denom))

    current.update({
        "id": len(episodes) + 1,
        "end": float(moves[-1]["end"]),
        "counts": counts,
        "coverage": round(coverage, 3),
        "avg_confidence": round(avg_conf, 3),
        "flow_score": round(flow_score, 3),
        "teacher_moves": teacher_moves,
        "student_moves": student_moves,
        "duration": round(max(0.0, moves[-1]["end"] - moves[0]["start"]), 3),
        "sequence": [mv["ohcr"] for mv in moves],
    })

    current["status"] = "complete" if all(counts.get(stage, 0) > 0 for stage in STAGE_ORDER) else "partial"
    quality_score = 0.45 * coverage + 0.4 * avg_conf + 0.15 * flow_score
    current["quality_score"] = round(min(max(quality_score, 0.0), 1.0), 3)
    episodes.append(current.copy())


def analyze_discourse_acts(utterances: List[Dict], *, preprocessed: bool = False) -> Dict:
    episodes: List[Dict] = []
    general_segments: List[Dict] = []
    general_buffer: List[Dict] = []
    current = None

    def flush_general():
        nonlocal general_buffer
        if not general_buffer:
            return
        segment = {
            "start": float(general_buffer[0]["start"]),
            "end": float(general_buffer[-1]["end"]),
            "utterance_count": len(general_buffer),
            "utterances": general_buffer.copy(),
        }
        general_segments.append(segment)
        general_buffer = []

    def start_episode(move_entry: Dict, stage_idx: int) -> Dict:
        return {
            "start": float(move_entry["start"]),
            "moves": [move_entry],
            "highest_stage": stage_idx,
            "order_violations": 0,
            "skipped_stages": 0,
            "status": "active",
        }

    def add_move(ep: Dict, move_entry: Dict, stage_idx: int) -> None:
        if ep["moves"]:
            if stage_idx < ep["highest_stage"]:
                ep["order_violations"] += 1
            elif stage_idx > ep["highest_stage"] + 1:
                ep["skipped_stages"] += stage_idx - ep["highest_stage"] - 1
        ep["moves"].append(move_entry)
        ep["highest_stage"] = max(ep["highest_stage"], stage_idx)
        ep["status"] = "complete" if ep["highest_stage"] >= STAGE_INDEX["R"] else "active"

    for idx, utt in enumerate(utterances):
        move = utt if preprocessed else _simplify_utterance(utt, idx)
        label = move["ohcr"]
        if label not in STAGE_INDEX:
            if current:
                _finalize_episode(episodes, current)
                current = None
            general_buffer.append(move)
            continue

        stage_idx = STAGE_INDEX[label]
        flush_general()

        if current is None:
            if label != "O":
                general_buffer.append(move)
                continue
            current = start_episode(move, stage_idx)
            continue

        if label == "O" and current["moves"]:
            _finalize_episode(episodes, current)
            current = start_episode(move, stage_idx)
            continue

        if stage_idx < current["highest_stage"] and label == "O":
            _finalize_episode(episodes, current)
            current = start_episode(move, stage_idx)
            continue

        add_move(current, move, stage_idx)

    if current:
        _finalize_episode(episodes, current)
    flush_general()

    complete = [ep for ep in episodes if ep["status"] == "complete"]
    partial = [ep for ep in episodes if ep["status"] != "complete"]
    avg_quality = round(sum(ep["quality_score"] for ep in episodes) / len(episodes), 3) if episodes else 0.0
    avg_coverage = round(sum(ep["coverage"] for ep in episodes) / len(episodes), 3) if episodes else 0.0

    summary = {
        "total_acts": len(episodes),
        "complete_acts": len(complete),
        "partial_acts": len(partial),
        "avg_quality_score": avg_quality,
        "avg_coverage": avg_coverage,
    }

    return {
        "episodes": episodes,
        "general_segments": general_segments,
        "summary": summary,
    }

def level_timeline(utterances: List[Dict], window_sec: int = 20) -> List[Dict]:
    if not utterances:
        return []
    window_sec = max(float(window_sec), 1e-9)
    half_window = window_sec / 2.0

    sorted_utts = sorted(
        (
            {
                "start": float(u.get("start", 0.0)),
                "end": float(u.get("end", 0.0)),
                "iam_level": int(u.get("iam_level", 1)),
                "iam_level_source": u.get("iam_level_source", "llm"),
            }
            for u in utterances
        ),
        key=lambda item: item["start"],
    )
    if not sorted_utts:
        return []

    limit = max(sorted_utts[-1]["end"], window_sec)
    times: List[float] = []
    t = 0.0
    while t <= limit:
        times.append(t)
        t += window_sec

    out = []
    for center in times:
        window_start = max(0.0, center - half_window)
        window_end = center + half_window

        total = 0
        level_sum = 0.0
        max_level = 0
        llm_count = 0
        fallback_count = 0

        for candidate in sorted_utts:
            start = candidate["start"]
            end = candidate["end"]
            if end < window_start or start > window_end:
                continue
            total += 1
            lvl = int(candidate.get("iam_level", 1))
            level_sum += lvl
            if lvl > max_level:
                max_level = lvl
            if candidate.get("iam_level_source") == "fallback":
                fallback_count += 1
            else:
                llm_count += 1

        if total == 0:
            out.append({"time": float(center), "level": 1, "count": 0, "avg_level": 1.0, "max_level": 1, "llm_count": 0, "fallback_count": 0})
            continue

        avg = level_sum / total
        blended = 0.6 * avg + 0.4 * max_level
        level = int(min(5, max(1, round(blended))))
        out.append({
            "time": float(center),
            "level": level,
            "avg_level": round(avg, 2),
            "max_level": max_level,
            "count": total,
            "llm_count": llm_count,
            "fallback_count": fallback_count,
        })
    return out

def ohcr_metrics(utterances: List[Dict], counts: Dict[str, int], challenge_indices: List[int]) -> Dict:
    cr_pairs = len(challenge_indices)
    cr_resolved = 0
    for idx in challenge_indices:
        if any(v.get("ohcr") == "R" for v in utterances[idx + 1 : idx + 4]):
            cr_resolved += 1
    cr_rate = (cr_resolved / cr_pairs) if cr_pairs else 0.0
    duration_min = (utterances[-1]["end"] / 60.0) if utterances else 1.0
    res_density = counts.get("R", 0) / max(duration_min, 1e-9)
    return {
        "ohcr_counts": counts,
        "challenge_resolve_rate": round(cr_rate, 3),
        "resolution_density_per_min": round(res_density, 3),
    }

def participation_metrics(role_totals: Dict[str, float], role_counts: Dict[str, int]) -> Dict:
    dur_teacher = role_totals.get("teacher", 0.0)
    dur_student = role_totals.get("student", 0.0)
    total = max(dur_teacher + dur_student, 1e-9)
    teacher_count = role_counts.get("teacher", 0)
    student_count = role_counts.get("student", 0)
    avg_teacher = (dur_teacher / teacher_count) if teacher_count else 0.0
    avg_student = (dur_student / student_count) if student_count else 0.0
    return {
        "teacher_talk_pct": round(dur_teacher / total, 3),
        "student_talk_pct": round(dur_student / total, 3),
        "avg_teacher_turn": round(avg_teacher, 3),
        "avg_student_turn": round(avg_student, 3),
    }

def beneficial_duration_pct(timeline: List[Dict], threshold: int = 3) -> float:
    if not timeline:
        return 0.0
    good = sum(1 for p in timeline if p["level"] >= threshold)
    return round(good / len(timeline), 3)

def kcs_score(timeline: List[Dict]) -> float:
    if not timeline:
        return 1.0
    levels = [p["level"] for p in timeline]
    return round(sum(levels) / len(levels), 3)

def _format_duration(seconds: float) -> str:
    if seconds <= 0:
        return "0s"
    total_seconds = int(round(seconds))
    minutes, sec = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if sec or not parts:
        parts.append(f"{sec}s")
    return " ".join(parts)


def compute_all(utterances: List[Dict], coach_report: Dict = None) -> Dict:
    simplified = [_simplify_utterance(u, idx) for idx, u in enumerate(utterances)]
    if not simplified:
        return {
            "ohcr_counts": {"O": 0, "H": 0, "C": 0, "R": 0, "None": 0},
            "challenge_resolve_rate": 0.0,
            "resolution_density_per_min": 0.0,
            "teacher_talk_pct": 0.0,
            "student_talk_pct": 0.0,
            "avg_teacher_turn": 0.0,
            "avg_student_turn": 0.0,
            "beneficial_duration_pct": 0.0,
            "kcs_score": 1.0,
            "timeline": [],
            "discourse_analysis": analyze_discourse_acts([]),
            "class_duration_sec": 0.0,
            "class_duration_formatted": "0s",
            "interaction_count": 0,
            "subtopic_count": 0,
            "teacher_question_count": 0,
            "student_question_count": 0,
            "topics": [],
            "observe_count": 0,
            "hypothesis_count": 0,
            "challenge_count": 0,
            "resolution_count": 0,
            "observe_context": "0 moves \u2022 \u201cWhat do we notice?\u201d Highlight concrete evidence before moving forward.",
            "hypothesis_context": "0 moves \u2022 \u201cWhat could explain the observation?\u201d Encourage learners to voice emerging theories.",
            "challenge_context": "0 moves \u2022 \u201cDoes this hypothesis hold up?\u201d Invite critique and stress-testing of ideas.",
            "resolution_context": "0 moves \u2022 \u201cWhat have we learned?\u201d Synthesize takeaways and close the loop together.",
        }

    counts = {"O": 0, "H": 0, "C": 0, "R": 0, "None": 0}
    role_totals = {"teacher": 0.0, "student": 0.0}
    role_counts = {"teacher": 0, "student": 0}
    challenge_indices: List[int] = []
    teacher_question_count = 0
    student_question_count = 0
    interaction_count = 0
    prev_role = None
    class_start = simplified[0]["start"]
    class_end = simplified[0]["end"]

    for idx, utt in enumerate(simplified):
        label = utt["ohcr"]
        counts[label] += 1
        if label == "C":
            challenge_indices.append(idx)

        role = utt["role"]
        if role in role_totals:
            role_totals[role] += utt.get("duration", 0.0)
            role_counts[role] += 1
        iam_int = utt.get("iam_level")
        if iam_int is None:
            utt["iam_level"] = 1
            utt["iam_level_source"] = "fallback"
        else:
            utt["iam_level"] = iam_int
            utt["iam_level_source"] = "llm"
        discourse_act = str(utt.get("discourse_act", "")).lower()
        if discourse_act == "question":
            if role == "teacher":
                teacher_question_count += 1
            elif role == "student":
                student_question_count += 1
        if role in {"teacher", "student"}:
            if prev_role and prev_role != role:
                interaction_count += 1
            prev_role = role
        class_start = min(class_start, utt["start"])
        class_end = max(class_end, utt["end"])

    timeline = level_timeline(simplified)
    ohcr = ohcr_metrics(simplified, counts, challenge_indices)
    participation = participation_metrics(role_totals, role_counts)
    class_duration_sec = max(0.0, class_end - class_start)

    topics: List[str] = []
    if isinstance(coach_report, dict):
        topics = [t for t in coach_report.get("topics", []) if isinstance(t, str)]

    def _stage_context(count: int, stage: str) -> str:
        prompts = {
            "Observe": "\u201cWhat do we notice?\u201d Highlight concrete evidence before moving forward.",
            "Hypothesis": "\u201cWhat could explain the observation?\u201d Encourage learners to voice emerging theories.",
            "Challenge": "\u201cDoes this hypothesis hold up?\u201d Invite critique and stress-testing of ideas.",
            "Resolve": "\u201cWhat have we learned?\u201d Synthesize takeaways and close the loop together.",
        }
        base = prompts[stage]
        if count <= 0:
            return f"0 moves \u2022 {base}"
        label = "move" if count == 1 else "moves"
        return f"{count} {label} \u2022 {base}"

    observe_count = counts.get("O", 0)
    hypothesis_count = counts.get("H", 0)
    challenge_count = counts.get("C", 0)
    resolution_count = counts.get("R", 0)

    return {
        **ohcr,
        **participation,
        "beneficial_duration_pct": beneficial_duration_pct(timeline),
        "kcs_score": kcs_score(timeline),
        "timeline": timeline,
        "discourse_analysis": analyze_discourse_acts(simplified, preprocessed=True),
        "class_duration_sec": round(class_duration_sec, 3),
        "class_duration_formatted": _format_duration(class_duration_sec),
        "interaction_count": interaction_count,
        "subtopic_count": len(topics),
        "teacher_question_count": teacher_question_count,
        "student_question_count": student_question_count,
        "topics": topics,
        "observe_count": observe_count,
        "hypothesis_count": hypothesis_count,
        "challenge_count": challenge_count,
        "resolution_count": resolution_count,
        "observe_context": _stage_context(observe_count, "Observe"),
        "hypothesis_context": _stage_context(hypothesis_count, "Hypothesis"),
        "challenge_context": _stage_context(challenge_count, "Challenge"),
        "resolution_context": _stage_context(resolution_count, "Resolve"),
    }
