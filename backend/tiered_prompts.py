import json
import time
from typing import Dict, List, Tuple

from openai import OpenAI

from backend.cache import SQLiteCache
from backend.config import CFG

client = OpenAI(api_key=CFG.openai_api_key)
cache = SQLiteCache(CFG.cache_db)

TIER_OUTPUT_SCHEMA = {
    "name": "tiered_prompt_output",
    "schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "paragraphs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [],
                        },
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "default": [],
                        },
                        "table": {
                            "type": "object",
                            "properties": {
                                "headers": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "rows": {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "notes": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "default": [],
                                },
                            },
                            "required": ["headers", "rows"],
                        },
                        "examples": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "label": {"type": "string"},
                                    "quote": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                    "annotation": {"type": "string"},
                                },
                                "required": ["label", "quote"],
                            },
                            "default": [],
                        },
                    },
                    "required": ["title"],
                },
            },
            "reliability_flags": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
            "notes": {
                "type": "array",
                "items": {"type": "string"},
                "default": [],
            },
        },
        "required": ["sections"],
        "additionalProperties": False,
    },
    "strict": True,
}

TIER_PROMPTS = [
    {
        "id": "tier1",
        "title": "Tier 1 – Basic Interaction Metrics",
        "description": "Descriptive stats with reliability checks on labelled turns.",
        "prompt": """You are an expert in classroom discourse analysis and educational analytics.
Your job is to perform **Tier 1: Basic Interaction Metrics (Descriptive Level)** analysis on a labelled classroom transcript, while also checking the reliability of the extracted data.

────────────────────────────
A. CONTEXT
────────────────────────────
The transcript contains speaker labels such as “Teacher:” and “Student 1:”, “Student 2:”, etc.
Each labelled utterance marks one **turn** (a change of speaker).

Goal: produce reliable descriptive statistics about participation (who spoke, how often, how long)
AND automatically check for data-quality issues or implausible values.

────────────────────────────
B. METRICS TO EXTRACT
────────────────────────────
Compute these metrics:

1. **Total number of turns**
2. **Average length of turn** (words per turn) for teacher & students
3. **Speaker proportion** (% of turns and % of total words: teacher vs all students)
4. **Number of unique students who spoke**
5. **Average time per contribution** (if timestamps exist)
6. **Number of teacher questions** (turns ending with “?” or containing interrogative words)
7. **Number of student questions**

────────────────────────────
C. RELIABILITY & SANITY CHECKS
────────────────────────────
For every metric computed, run the following checks and explicitly report if the transcript passes or fails:

1. **Speaker Tag Consistency Check**
   - Are all turns properly labelled (Teacher or Student X)?
   - Flag if unlabelled lines exceed 2 % of total turns.

2. **Turn Balance Check**
   - Compute teacher : student turn ratio.
   - If one side > 90 % of turns, flag:
     “⚠ Extreme imbalance—possible transcription or segmentation error.”

3. **Word-Count Plausibility Check**
   - If average teacher turn < 2 words or > 50 words, flag “⚠ Suspicious teacher turn length.”
   - Same for students.

4. **Participation Spread Check**
   - If fewer than 2 students speak → flag “⚠ Low diversity of speakers.”
   - If one student contributes > 60 % of student turns → flag “⚠ Dominant student detected.”

5. **Question Detection Sanity Check**
   - Compare teacher questions vs total teacher turns.
   - If > 60 % or < 2 % of turns are questions, flag “⚠ Possible punctuation bias.”

6. **Text Completeness Check**
   - If last line is truncated or dialogue ends mid-sentence → flag “⚠ Incomplete transcript.”

7. **Cross-Metric Coherence Check**
   - Verify that % of turns + % of words ≈ 100 ± 5 %.
   - If not, flag arithmetic inconsistency.

────────────────────────────
D. OUTPUT FORMAT
────────────────────────────

**SECTION 1 – Quantitative Summary**

| Metric | Teacher | Students | Notes |
|---------|----------|-----------|-------|
| Total Turns |  |  |  |
| Avg Turn Length (words) |  |  |  |
| % of Total Turns |  |  |  |
| % of Total Words |  |  |  |
| Unique Student Speakers | — |  |  |
| Avg Time / Turn (sec) |  |  |  |
| No. of Questions |  |  |  |

**SECTION 2 – Descriptive Interpretation**

Provide 1–2 paragraphs interpreting what the numbers mean:
- “Teacher spoke 68 % of total words, indicating lecture-dominant flow.”
- “Six students participated, but two generated 70 % of student turns, suggesting uneven engagement.”

**SECTION 3 – Reliability Comment**

Summarize overall trustworthiness:
> “Metrics appear reliable within expected ranges; no major anomalies detected.”
OR
> “Data shows multiple imbalance flags—interpretation should be cautious.”

────────────────────────────
E. STYLE RULES
────────────────────────────
- Quantify first, interpret second.
- Always show numbers.
- Do **not** hide or silently fix anomalies—always report them.

────────────────────────────
F. OUTPUT JSON FORMAT
────────────────────────────
Return your entire analysis as JSON matching this structure:
{
  "summary": "Short recap of Tier 1 findings",
  "sections": [
    {
      "title": "SECTION X – ...",
      "paragraphs": ["text"],
      "bullets": ["item"],
      "table": { "headers": ["Metric", "Teacher", ...], "rows": [["Total Turns", "12", "8", ""], ...], "notes": ["clarify checks"] }
    }
  ],
  "reliability_flags": ["Flag text"],
  "notes": ["Any extra clarifications"]
}
- Encode the quantitative table from Section 1 using the `table` field.
- List each named section (Section 1/2/3) as its own entry in `sections` with the exact section title.
- Use `paragraphs` or `bullets` arrays for prose instead of Markdown. Do not emit Markdown tables; only use the JSON table.

────────────────────────────
G. NOW START THE TASK
────────────────────────────
I will now provide the classroom transcript.

TRANSCRIPT STARTS BELOW:
------------------------
{transcript}
------------------------

Compute metrics, run all reliability checks, and produce **SECTION 1–3** exactly in that order.""",
    },
    {
        "id": "tier2",
        "title": "Tier 2 – Interaction Patterns",
        "description": "Structural exchange map (IRE / IRF / OHCR) with loop ratios.",
        "prompt": """You are an expert in classroom discourse analysis and learning sciences.
Your task is to perform **Tier 2: Interaction Patterns (Structural Level)** analysis on a labelled class discussion transcript.

────────────────────────
A. OVERALL GOAL
────────────────────────
You will analyse the transcript to understand **how turns connect** and **what kind of exchange structures** occurred.

You are NOT yet judging deep learning or knowledge construction (that comes in another tier).
Here, you are answering:

> “Structurally, what kind of conversation was this?
> Was it mostly IRE-style quizzing, IRF-style extended checks, or OHCR-style reasoning cycles?
> How often did the class loop back and forth before closing a topic?”

In other words, we want to understand *how the dialogue moved*, not yet *what was learned*.

────────────────────────
B. KEY CONCEPTS & DEFINITIONS
────────────────────────

1. **Turn**
   - One speaker’s utterance until the next speaker takes over.
   - The transcript should have labels like “Teacher: …”, “Student 1: …”, etc.

2. **Episode (or Exchange)**
   - A short cluster of turns that revolve around a **single local task or question**.
   - Example of an episode:
     - Teacher asks a question,
     - 1–3 students respond,
     - Teacher closes or shifts topic.
   - You will segment the transcript into episodes for pattern labeling.

3. **Interaction Patterns to Detect**

   a) **IRE Pattern (Initiate–Respond–Evaluate)**
   - Structure:
     1. **Initiate (I)** – typically the teacher asks a question to check or prompt knowledge.
     2. **Respond (R)** – a student gives an answer.
     3. **Evaluate (E)** – the teacher judges, confirms, or rejects the answer (“Correct”, “No”, “Yes, exactly”).
   - Function: Mainly to **test or display knowledge**, not to explore.
   - Example:
     - T: “What is brand equity?” (I)
     - S: “It’s the value a brand adds to a product.” (R)
     - T: “Correct.” (E)

   b) **IRF Pattern (Initiate–Respond–Follow-up)**
   - Similar to IRE but the final teacher move is **not just evaluation**, it extends the dialogue.
   - Structure:
     1. **Initiate (I)** – teacher question.
     2. **Respond (R)** – student answer.
     3. **Follow-up (F)** – teacher probes, asks for examples, or pushes thinking further.
   - Function: Slightly more open and dialogic than IRE.
   - Example:
     - T: “What is segmentation?” (I)
     - S: “Dividing the market into groups.” (R)
     - T: “Okay, can you give me a real example from food delivery apps?” (F)

   c) **OHCR Sequence (Observe–Hypothesize–Challenge–Resolve)**
   - A multi-turn reasoning pattern aligned with the OHCR framework.
   - Not necessarily 4 turns only; it can be extended (e.g., O–H–H–C–C–R).
   - Defined functionally:
     - **Observe (O)** – Teacher or student draws attention to a phenomenon, data, graph, case, or situation (“Look at this chart…”).
     - **Hypothesize (H)** – Students propose explanations, reasons, or mechanisms (“Maybe demand is higher because…”).
     - **Challenge (C)** – Teacher or students bring up counterexamples, exceptions, or contradictions to test hypotheses (“But if that’s true, why did sales drop here?”).
     - **Resolve (R)** – The group arrives at a clearer formulation, principle, or refined understanding (“So it’s not just price, it’s also perceived risk.”).
   - OHCR episodes may be overlapping with IRF structurally, but they are longer and built around progressive refinement.

   d) **Loop Ratio**
   - The **average number of back-and-forth exchanges before a topic is closed**.
   - Roughly: per episode, how many turns happen from the first teacher initiation to the final closure (shift of topic)?
   - Higher loop ratio → more extended exploration/collaboration.

────────────────────────
C. ANALYSIS PROCEDURE (STEP-BY-STEP)
────────────────────────

When you receive the transcript:

1. **Parse and Segment into Episodes**
   - Read through the transcript once.
   - Segment it into coherent **episodes**, where:
     - One main question, prompt, or problem is being addressed.
     - The episode ends when the teacher clearly closes the topic or shifts to something new.
   - Give each episode an ID (Episode 1, Episode 2, etc.).

2. **Identify the Dominant Pattern per Episode**
   - For each episode, decide which pattern best describes its structure:
     - **Pure IRE**
     - **Pure IRF**
     - **Dominantly OHCR**
     - **Mixed / Other** (if no clear pattern dominates)
   - IMPORTANT: Use **functional logic**, not just punctuation.
     - An “Evaluate” move = teacher closing judgement.
     - A “Follow-up” move = teacher extending thinking.
     - “Challenge” = explicit testing of a hypothesis against a counterexample or tricky case.
     - “Resolve” = summarizing and stabilizing understanding.

3. **Annotate OHCR Internally (When Present)**
   - For any episode you classify as OHCR (or partially OHCR), identify where each component occurs:
     - Mark lines as O / H / C / R (even roughly, like “O at turn 12”, “H at 14–16”).
   - If an episode has O and H but no clear C, mark it as **Partial OHCR (O–H only)**.

4. **Count Pattern Frequencies**
   - Count:
     - Number of IRE episodes.
     - Number of IRF episodes.
     - Number of OHCR (full or partial) episodes.
     - Number of “Other / Mixed” episodes.
   - Estimate each as a proportion of total episodes (e.g., 60% IRE, 25% IRF, 15% OHCR).

5. **Estimate Loop Ratio**
   - For each episode, count how many turns are in that episode.
   - Compute/estimate:
     - **Average turns per episode** (loop ratio).
     - Optionally, note min and max (e.g., shortest = 3 turns, longest = 14 turns).

────────────────────────
D. RELIABILITY & SANITY CHECKS
────────────────────────

While doing this, run these internal checks and explicitly report them:

1. **Pattern Labelling Consistency**
   - Don’t force OHCR where there is no real challenge or resolution.
   - If uncertain whether something is IRE or IRF, say so and mark as **Mixed / Ambiguous**.

2. **Sufficiency of Evidence**
   - Only call an episode **OHCR** if:
     - There is at least one observation (O) and
     - At least one genuine hypothesis from students (H).
   - If challenge (C) or resolve (R) is weak, call it:
     - “Partial OHCR” and explain which parts are present.

3. **Extreme Cases Check**
   - If > 80% of episodes are tagged as IRE, note that the session was **heavily IRE-dominant** and check if you might be over-labelling (e.g., teacher monologue with no student response is not IRE; it’s just lecturing).
   - If you label **everything** as OHCR, re-examine 2–3 episodes and confirm that:
     - Multiple hypotheses were genuinely explored, not just one student answer and teacher explanation.

4. **Alignment with Tier 1 Metrics (if known)**
   - If earlier metrics showed very low student talk, it is unlikely to have many full OHCR episodes.
   - Flag and comment if there is a mismatch (e.g., low student words but many OHCR labels).

────────────────────────
E. OUTPUT FORMAT
────────────────────────

Structure your answer into these sections:

**SECTION 1 – Quick Recap of Pattern Definitions (2–4 lines)**
In your own words, briefly restate what you mean by IRE, IRF, and OHCR, just to show understanding.

---

**SECTION 2 – Episode-wise Pattern Map (Structured List or Table)**

For each episode, provide:

- Episode ID (e.g., Episode 1)
- Dominant Pattern (IRE / IRF / OHCR / Partial OHCR / Other)
- Approximate turn range (e.g., turns 1–9)
- Very short description of what happens.

Example format:

- Episode 1 (turns 1–7): **IRE**
  - T asks for definition of regression; S gives answer; T confirms and moves on.

- Episode 2 (turns 8–18): **OHCR (full)**
  - T presents a confusing graph (O); Students propose explanations (H); T brings a counterexample (C); Class settles on proper interpretation (R).

- Episode 3 (turns 19–25): **IRF**
  - T asks factual question; S responds; T probes for example and slight extension.

You do NOT have to list every tiny detail, but you should cover all major episodes.

---

**SECTION 3 – Pattern Frequency & Loop Ratio Summary**

Provide a small table summarising counts and proportions:

Example:

| Pattern Type       | Count of Episodes | Approx. % of Total |
|--------------------|-------------------|--------------------|
| IRE                | 7                 | ~50%               |
| IRF                | 3                 | ~21%               |
| OHCR (full)        | 2                 | ~14%               |
| Partial OHCR       | 1                 | ~7%                |
| Other/Mixed        | 1                 | ~7%                |

Also state:

- Average turns per episode (loop ratio)
- Shortest and longest episode lengths.

---

**SECTION 4 – Representative Examples**

For each major pattern actually present (IRE, IRF, OHCR/Partial OHCR), give **one short quoted example** from the transcript:

- Quote a few consecutive turns.
- Under the quote, annotate which turns are I, R, E, F, O, H, C, R.

Example:

> **Example of IRE**
> T: “What is brand equity?” (I)
> S1: “Value added by brand to the product.” (R)
> T: “Correct, that’s the textbook definition.” (E)

> **Example of OHCR**
> T: “Look at this demand curve after the price change.” (O)
> S2: “Maybe customers didn’t notice the price difference.” (H)
> T: “But high-value customers reduced usage – how do we explain that?” (C)
> S3: “Maybe they’re more price-sensitive because of alternatives.” (H)
> T: “Right, so we see segmentation in elasticity.” (R)

---

**SECTION 5 – Structural Narrative: What Happened in This Discussion?**

In 1–3 paragraphs, describe the **overall structural character** of the class:

- Was it mostly teacher-controlled testing (IRE-heavy)?
- Were there pockets of deeper exploration (some OHCR)?
- Did the teacher often follow up after answers (IRF)?
- Did episodes stay short (low loop ratio) or extend (high loop ratio)?

Example style:

> “The session was predominantly IRE-based, with the teacher asking short recall questions and quickly evaluating answers. There were two clear OHCR episodes where students were invited to interpret graphs and reconcile contradictions, but these were the exception rather than the norm. Overall loop ratio was low (average 5 turns per episode), indicating relatively short exchanges before topics were closed.”

---

**SECTION 6 – Reliability & Ambiguity Notes**

Explicitly comment on:

- How confident you are in pattern labels.
- Where you had to mark “Partial OHCR” or “Mixed”.
- Any episodes that were especially ambiguous and why.

Example:

> “Pattern labels should be treated as approximate. In Episodes 4 and 6, follow-up questions blurred the line between IRE and IRF. Similarly, one segment was labelled Partial OHCR because students hypothesised but there was no clear challenge phase.”

────────────────────────
F. STYLE & CONSTRAINTS
────────────────────────

- Be explicit, concrete, and anchored in the transcript.
- Never force a pattern that isn’t really there; it is okay to say “unclear.”
- Do not drift into evaluating knowledge construction or learning outcomes here; stay at the structural/interaction level.
- Use the terms IRE, IRF, OHCR, Partial OHCR, and Other/Mixed consistently.

────────────────────────
G. OUTPUT JSON FORMAT
────────────────────────
Return JSON that follows this structure:
{
  "summary": "Concise Tier 2 recap",
  "sections": [
    {
      "title": "SECTION X – ...",
      "paragraphs": ["..."],
      "bullets": ["..."],
      "table": {"headers": ["Pattern Type", ...], "rows": [["IRE", "7", "50%"], ...]},
      "examples": [{"label": "Example of IRE", "quote": ["T: ...", "S: ..."], "annotation": "I/R/E mapping"}]
    }
  ],
  "reliability_flags": ["Note on ambiguous Episode 4", ...]
}
- Each of the six mandated sections must appear once in `sections` using their exact headings.
- Encode pattern frequency and loop ratio as a `table` inside Section 3.
- Represent representative quotes inside Section 4 using the `examples` array.
- Avoid Markdown; rely on the JSON fields only.

────────────────────────
H. NOW START THE TASK
────────────────────────

I will now provide the labelled class transcript.

TRANSCRIPT STARTS BELOW:
------------------------
{transcript}
------------------------

Follow the steps above and produce **SECTION 1–6** exactly in that order.""",
    },
    {
        "id": "tier3",
        "title": "Tier 3 – Knowledge Construction",
        "description": "IAM knowledge sharing vs construction diagnosis with feedback.",
        "prompt": """You are an expert in learning sciences, classroom discourse, and social constructivist pedagogy.
Your job is to perform **Tier 3: Knowledge Sharing and Knowledge Construction Analysis** on a labelled classroom transcript.

────────────────────────────
A. PURPOSE
────────────────────────────
You will:
1. Classify and interpret each major segment of the transcript as **Knowledge Sharing** or **Knowledge Construction** using IAM (Interaction Analysis Model) logic.
2. Diagnose the **depth of learning** — which IAM phase(s) the dialogue reached.
3. Provide **practical feedback** to the teacher, including examples of how to push the conversation toward higher IAM phases (III → V).
4. Summarise the overall learning quality of the class.

────────────────────────────
B. THEORETICAL FRAMEWORK
────────────────────────────

1. **Knowledge Sharing**
   - Transfer of information or explanation from teacher to students.
   - Students mostly listen or recall known facts.
   - No reasoning, contradiction, or synthesis.
   - Corresponds to **IAM Phases I–II** (Sharing / Discovering Dissonance only superficially).

2. **Knowledge Construction**
   - Learners generate, test, and refine ideas through reasoning.
   - Discussion involves challenge, negotiation, and synthesis.
   - Corresponds to **IAM Phases III–V**:
     - **III – Negotiation of meaning**
     - **IV – Testing & modification**
     - **V – Agreement & application**

3. **Engagement vs Participation**
   - Participation = talking.
   - Engagement = cognitive effort.
     A silent reflection moment can still signal construction if it follows active reasoning.

────────────────────────────
C. ANALYTICAL STEPS
────────────────────────────

1. **Segment the Transcript**
   - Use the episode segmentation already established in Tier 2.
   - For each episode, identify key turns that show idea generation, challenge, or resolution.

2. **Label the Dominant Nature of Each Episode**
   - **Knowledge Sharing**
     → teacher explains or confirms; students recall or agree.
   - **Knowledge Construction**
     → students or teacher-student jointly reason, challenge, and refine.

3. **Identify IAM Phase Reached**
   - Decide which IAM phase (I → V) best fits each episode.
   - If multiple phases appear, record the *highest* phase reached.
   - Examples of coding logic:
     - Factual recall → Phase I
     - Simple contradiction → Phase II
     - Clarification / negotiation → Phase III
     - Evidence testing → Phase IV
     - Consensus / new principle → Phase V

4. **Provide Micro-Feedback per Episode**
   - For each episode, explain:
     - What kind of discourse occurred.
     - Why it qualifies as that IAM phase.
     - **One specific suggestion**: how the teacher could push it one phase higher next time.

     Example:
     > “Episode 2 stayed in Phase II because students stated opposing views but did not reconcile them.
     > You could ask, *‘Which evidence supports each view?’* to move toward Phase III.”

5. **Synthesize Across the Whole Class**
   - Estimate proportions:
     - % of segments in Sharing vs Construction.
     - Distribution across IAM phases I–V.
   - Interpret the overall learning depth.

────────────────────────────
D. OUTPUT FORMAT
────────────────────────────

**SECTION 1 – Conceptual Recap (2–4 lines)**
Briefly restate, in your own words, what knowledge sharing and knowledge construction mean.

---

**SECTION 2 – Episode-wise Analysis Table**

| Episode | Dominant Nature | Highest IAM Phase | Evidence (1–2 lines from transcript) | Feedback to Improve |
|----------|-----------------|------------------|--------------------------------------|---------------------|
| 1 | Sharing | I | “Teacher explains formula; students nod.” | Ask students *why* the formula works → triggers reasoning (Phase II–III). |
| 2 | Construction | III | “Students debate why campaign failed.” | Push them to test ideas with data → Phase IV. |
| … | … | … | … | … |

---

**SECTION 3 – Aggregate Summary**

| Category | Count / % | Description |
|-----------|------------|-------------|
| Knowledge Sharing Episodes |  |  |
| Knowledge Construction Episodes |  |  |
| Phase I |  |  |
| Phase II |  |  |
| Phase III |  |  |
| Phase IV |  |  |
| Phase V |  |  |

Include 2–3 sentences interpreting these numbers:
> “About 65 % of episodes stayed in sharing (Phases I–II).
> Only two episodes reached Phase IV → testing evidence; none achieved full consensus (Phase V).”

---

**SECTION 4 – Feedback and Improvement Suggestions**

Provide a narrative synthesis of actionable advice:

1. **Macro Feedback (Overall Teaching Style)**
   - How teacher talk vs student reasoning affected learning depth.
   - Whether questions encouraged higher-order thinking.
   - How discourse balance could be improved.

2. **Micro Feedback (Illustrated Examples)**
   - Quote 2–3 specific lines where discourse could be deepened.
   - For each, rewrite the teacher’s next possible move to push into a higher IAM phase.

   Example:

   **Original**
   > T: “Good, so price affects demand. Next topic.”

   **Better (to reach Phase III–IV)**
   > T: “Interesting—can anyone think of a case where price didn’t affect demand? What might explain that?”

   Explain why this modification promotes negotiation and testing.

3. **Phase V Targeting**
   - Suggest a closing move that would help the class *resolve* ideas collaboratively.
   - Example: “Summarise what everyone agrees on and apply it to a new case—this converts construction into collective knowledge creation.”

---

**SECTION 5 – Overall Narrative Diagnosis**

In 1–3 short paragraphs, describe what actually happened cognitively in this class:
- How far the collective reasoning progressed.
- Whether students built shared understanding.
- The balance between transmission and exploration.
- The general tone of teacher feedback and responsiveness.

Finish with a concise assessment such as:
> “This class demonstrated solid engagement but remained largely in IAM Phases II–III.
> Introducing counterexamples and collective synthesis could elevate it to Phase V.”

────────────────────────────
E. RELIABILITY & SANITY CHECKS
────────────────────────────
At the end of your analysis, explicitly verify:

1. **Phase Distribution Plausibility**
   - If all episodes are Phase V, re-evaluate; such perfection is unlikely.
   - If all are Phase I, ensure you’re not missing subtle reasoning.

2. **Alignment with Tier 1/2 Data (if available)**
   - If teacher dominated 90 % of turns, frequent Phase IV–V may be unrealistic—flag mismatch.

3. **Feedback Specificity Check**
   - Each feedback example must quote or paraphrase actual transcript lines.
   - Avoid generic advice (“Be more interactive” is invalid).

────────────────────────────
F. STYLE
────────────────────────────
- Be concrete, evidence-based, and actionable.
- Use IAM terminology explicitly (Phase I → V).
- Keep tone developmental and professional, as if writing feedback for a peer-teacher workshop.

────────────────────────────
G. OUTPUT JSON FORMAT
────────────────────────────
Return JSON using this structure:
{
  "summary": "Overall Tier 3 recap",
  "sections": [
    {
      "title": "SECTION X – ...",
      "paragraphs": ["..."],
      "bullets": ["..."],
      "table": {"headers": ["Episode", "Nature", ...], "rows": [["1", "Sharing", "I", "quote", "feedback"], ...]},
      "examples": [{"label": "Micro Feedback Example", "quote": ["T: ..."], "annotation": "Revised prompt"}]
    }
  ],
  "reliability_flags": ["Phase distribution plausible"],
  "notes": ["Mention alignment with Tier 1/2 if relevant"]
}
- Use Section titles 1–5 verbatim so the frontend can map them.
- Encode the Episode-wise analysis table (Section 2) and aggregate summary table (Section 3) via the `table` object.
- Place feedback exemplars inside Section 4 using `examples` entries (each with label/quote/annotation describing the improved move).
- Keep prose in `paragraphs` or `bullets`; avoid markdown formatting.

────────────────────────────
H. NOW START THE TASK
────────────────────────────
I will now provide the labelled transcript.

TRANSCRIPT STARTS BELOW:
------------------------
{transcript}
------------------------

Perform the Tier 3 analysis following steps A–F and output **SECTION 1–5** in order.""",
    },
]


def _expand_prompt(prompt: str, transcript: str) -> str:
    return prompt.replace("{transcript}", transcript)


def _format_transcript(utterances: List[Dict]) -> str:
    student_labels: Dict[str, str] = {}
    student_counter = 1
    lines: List[str] = []

    for utt in utterances:
        text = (utt.get("text") or "").strip()
        if not text:
            continue

        role = str(utt.get("role", "")).lower()
        speaker = (utt.get("speaker") or "").strip()

        if role == "teacher":
            label = "Teacher"
        elif role == "student":
            key = speaker or f"student_{student_counter}"
            if key not in student_labels:
                student_labels[key] = f"Student {student_counter}"
                student_counter += 1
            label = student_labels[key]
        else:
            label = speaker or "Speaker"

        lines.append(f"{label}: {text}")

    if not lines:
        return "Teacher: (Transcript unavailable.)"
    return "\n".join(lines)


def _default_structured_output(message: str) -> Dict:
    return {
        "summary": message,
        "sections": [
            {
                "title": "Status",
                "paragraphs": [message],
                "bullets": [],
            }
        ],
        "reliability_flags": [message],
        "notes": [],
    }


def _call_prompt(full_prompt: str) -> Tuple[Dict, Dict]:
    if not CFG.use_llm or not CFG.openai_api_key:
        return (
            _default_structured_output("LLM disabled or API key missing. Unable to run tiered prompt."),
            {"source": "fallback", "reason": "llm_disabled_or_missing_key"},
        )

    def _compute():
        last_err = None
        for attempt in range(3):
            try:
                if getattr(client, "responses", None):
                    response = client.responses.create(
                        model=CFG.llm_model,
                        temperature=0.2,
                        top_p=0.9,
                        input=[{"role": "user", "content": [{"type": "text", "text": full_prompt}]}],
                        response_format={"type": "json_schema", "json_schema": TIER_OUTPUT_SCHEMA},
                        timeout=90,
                    )
                    text = response.output[0].content[0].text
                    usage = getattr(response, "usage", None)
                else:
                    resp = client.chat.completions.create(
                        model=CFG.llm_model,
                        temperature=0.2,
                        top_p=0.9,
                        messages=[{"role": "user", "content": full_prompt}],
                        response_format={"type": "json_schema", "json_schema": TIER_OUTPUT_SCHEMA},
                        timeout=90,
                    )
                    text = (resp.choices[0].message.content or "").strip()
                    usage = getattr(resp, "usage", None)
                data = json.loads(text)
                if not isinstance(data, dict):
                    raise ValueError("Tier output is not a JSON object")

                meta = {}
                if usage is not None:
                    meta = {
                        "ptoks": getattr(usage, "prompt_tokens", None),
                        "ctoks": getattr(usage, "completion_tokens", None),
                    }
                meta.setdefault("source", "llm")
                return data, meta
            except Exception as err:
                last_err = err
                time.sleep(0.8 * (attempt + 1))

        message = f"Unable to complete analysis due to repeated errors: {last_err}"
        return (
            _default_structured_output(message),
            {"source": "fallback", "error": str(last_err) if last_err else "unknown"},
        )

    payload = {
        "v": "tier_prompts_v2",
        "model": CFG.llm_model,
        "prompt_body": full_prompt,
    }
    return cache.get_or_set(payload, _compute)


def run_tiered_prompts(utterances: List[Dict]) -> Dict:
    transcript = _format_transcript(utterances)
    results = []

    for tier in TIER_PROMPTS:
        prompt = _expand_prompt(tier["prompt"], transcript)
        start = time.perf_counter()
        output, meta = _call_prompt(prompt)
        duration_ms = int((time.perf_counter() - start) * 1000)
        results.append(
            {
                "id": tier["id"],
                "title": tier["title"],
                "description": tier["description"],
                "output": output,
                "duration_ms": duration_ms,
                "meta": meta,
            }
        )

    return {"transcript": transcript, "results": results}
