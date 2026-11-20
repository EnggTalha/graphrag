"""Load and normalize evaluation questions from a JSON file."""

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

DEFAULT_QUESTIONS_PATH = os.path.join("data", "eval_questions.json")


@dataclass
class EvalQuestion:
    id: str
    question: str
    expected: Optional[str] = None
    notes: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


def load_questions(path: str = DEFAULT_QUESTIONS_PATH) -> List[EvalQuestion]:
    """
    Load questions from a JSON file.

    The file must contain a JSON list. Each item is either a string (treated as the
    question text) or an object with at least a ``question`` field and optional ``id``,
    ``expected`` and ``notes`` fields. Unknown fields are preserved in ``extra``.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Evaluation questions file not found: {path}. "
            "Create it or pass --questions with a valid path."
        )

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list of questions.")

    questions: List[EvalQuestion] = []
    for idx, item in enumerate(data):
        if isinstance(item, str):
            questions.append(EvalQuestion(id=f"q{idx + 1}", question=item))
            continue
        if not isinstance(item, dict):
            raise ValueError(
                f"Question #{idx + 1} in {path} must be a string or object."
            )
        text = item.get("question")
        if not text:
            raise ValueError(f"Question #{idx + 1} in {path} is missing 'question'.")
        known = {"id", "question", "expected", "notes"}
        extra = {k: v for k, v in item.items() if k not in known}
        questions.append(
            EvalQuestion(
                id=str(item.get("id") or f"q{idx + 1}"),
                question=text,
                expected=item.get("expected"),
                notes=item.get("notes"),
                extra=extra,
            )
        )

    if not questions:
        raise ValueError(f"No questions found in {path}.")
    return questions
