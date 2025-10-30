from typing import List, Literal, TypedDict

OHCR = Literal["O", "H", "C", "R", "None"]
Act = Literal["question", "statement", "regulatory", "other"]
Role = Literal["teacher", "student", "unknown"]

class Utterance(TypedDict):
    start: float
    end: float
    text: str
    speaker: str  # SPEAKER_0/1
    role: Role
