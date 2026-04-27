"""
ai_parser.py — Demo-mode natural language task extractor.

Runs fully offline with no external dependencies beyond stdlib and
pawpal_system. Parses free-text pet-care requests into Task objects using
regex patterns and keyword tables.

Optional LLM mode is intentionally NOT included in Phase 1 to keep the
system reliable and dependency-free. Notes for future integration are
left in comments where the hook would go.
"""
import re
from typing import Optional

from pawpal_system import Task
from safecare_logger import get_logger

logger = get_logger("ai_parser")

# ---------------------------------------------------------------------------
# Pattern tables
# ---------------------------------------------------------------------------

# Matches: "at 8am", "at 8:30am", "at 14:00", "at 6 pm"
_TIME_RE = re.compile(
    r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b",
    re.IGNORECASE,
)

# Duration extractors — each is (compiled_regex, int_extractor_fn)
_DURATION_PATTERNS: list[tuple[re.Pattern, object]] = [
    (re.compile(r"\b(\d+)\s*-?\s*(?:minutes?|mins?)\b", re.IGNORECASE),
     lambda m: int(m.group(1))),
    (re.compile(r"\b(\d+)\s*-?\s*hours?\b", re.IGNORECASE),
     lambda m: int(m.group(1)) * 60),
    (re.compile(r"\bhalf\s+an?\s+hour\b", re.IGNORECASE),
     lambda m: 30),
    (re.compile(r"\b(\d+)\s*h\b"),
     lambda m: int(m.group(1)) * 60),
]

# task_type → list of trigger keywords (checked in order; first match wins)
_TASK_TYPE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("medication", [
        "medication", "medicine", "med ", "meds", " pill", "pills",
        "tablet", "tablets", "capsule", "dose", "drug", "treatment",
        "supplement", "vitamin",
    ]),
    ("feeding", [
        "feed", "feeding", "meal", "meals", "food", "eat", "dinner",
        "breakfast", "lunch", "snack", "kibble", "wet food", "dry food",
        "water bowl",
    ]),
    ("exercise", [
        "walk", "walking", "walks", "run", "runs", "running", "jog",
        "exercise", "play outside", "hike", "outdoor",
    ]),
    ("grooming", [
        "groom", "grooming", "brush", "brushing", "bath", "bathe",
        "bathing", "nail", "nails", "trim", "clip", "ear clean",
    ]),
    ("enrichment", [
        "play", "playing", "toy", "toys", "enrich", "enrichment",
        "training", "train", "puzzle", "socialize",
    ]),
    ("vet", [
        "vet", "veterinarian", "checkup", "check-up", "appointment",
        "clinic", "vaccination", "vaccine",
    ]),
]

_DOSAGE_TASK_RE = re.compile(
    r"\b\d+\s*(?:mg|ml|g)\b|\b\d+\s+(?:tablet|pill|capsule)s?\b",
    re.IGNORECASE,
)

_DEFAULT_DURATIONS: dict[str, int] = {
    "medication": 5,
    "feeding": 15,
    "exercise": 30,
    "grooming": 20,
    "enrichment": 20,
    "vet": 60,
    "other": 15,
}

_PRIORITY_BY_TYPE: dict[str, int] = {
    "medication": 5,
    "vet": 5,
    "feeding": 4,
    "exercise": 3,
    "grooming": 2,
    "enrichment": 2,
    "other": 1,
}

# Noise prefixes stripped before building a task title
_PREFIX_RE = re.compile(
    r"^(?:my\s+)?(?:dog|cat|rabbit|bunny|pet|animal)(?:\s+\w+)?\s+(?:needs?\s+(?:a|an|to)\s+|needs?\s+)?",
    re.IGNORECASE,
)
_NEEDS_RE = re.compile(r"^(?:needs?\s+(?:a|an|to)\s+|needs?\s+)", re.IGNORECASE)
_LEADING_RE = re.compile(r"^(?:and|for|a|an|the)\s+", re.IGNORECASE)
_TRAILING_JUNK_RE = re.compile(r"[,;.\-\s]+$")

# Patterns removed from title text (time/duration noise)
_STRIP_FOR_TITLE: list[re.Pattern] = [
    _TIME_RE,
    re.compile(r"\bfor\s+\d+\s*(?:minutes?|mins?|hours?|h)\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*(?:minutes?|mins?|hours?|h)\b", re.IGNORECASE),
    re.compile(r"\bhalf\s+an?\s+hour\b", re.IGNORECASE),
    re.compile(r"\b\d+\s*h\b"),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_time(text: str) -> Optional[str]:
    """Return 'HH:MM' if a time expression is found, else None."""
    m = _TIME_RE.search(text)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    meridiem = (m.group(3) or "").lower()
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute:02d}"


def _extract_duration(text: str) -> Optional[int]:
    """Return duration in minutes if found, else None."""
    for pattern, extractor in _DURATION_PATTERNS:
        m = pattern.search(text)
        if m:
            return extractor(m)
    return None


def _has_task_keyword(text: str) -> bool:
    lower = text.lower()
    for _, keywords in _TASK_TYPE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return True
    return bool(_DOSAGE_TASK_RE.search(text))


def _detect_task_type(text: str) -> str:
    """Return the first matching task type or 'other'."""
    if _DOSAGE_TASK_RE.search(text):
        return "medication"
    lower = text.lower()
    for task_type, keywords in _TASK_TYPE_KEYWORDS:
        if any(kw in lower for kw in keywords):
            return task_type
    return "other"


def _build_title(segment: str, task_type: str) -> str:
    """Derive a clean task title from the raw segment text."""
    text = segment.strip()

    # Strip leading "my dog Max needs a …" boilerplate
    text = _PREFIX_RE.sub("", text)
    text = _NEEDS_RE.sub("", text)

    # Remove time and duration noise
    for pat in _STRIP_FOR_TITLE:
        text = pat.sub("", text)

    # Remove trailing "for" / "at" orphans
    text = re.sub(r"\s+(?:for|at)\s*$", "", text, flags=re.IGNORECASE)

    # Clean up leading conjunctions/articles and trailing punctuation
    text = _LEADING_RE.sub("", text.strip())
    text = _TRAILING_JUNK_RE.sub("", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Truncate and capitalise
    title = text[:55].strip()
    return title.capitalize() if title else task_type.capitalize()


def _split_on_and(text: str) -> list[str]:
    """Split on 'and' only where both sides have distinct task types."""
    for m in re.finditer(r"\band\b", text, re.IGNORECASE):
        left = text[:m.start()].strip()
        right = text[m.end():].strip()
        if (
            _has_task_keyword(left)
            and _has_task_keyword(right)
            and _detect_task_type(left) != _detect_task_type(right)
        ):
            return [left] + _split_on_and(right)
    return [text]


def _split_segments(text: str) -> list[str]:
    """Split a multi-task request into individual segments on commas/semicolons/and."""
    text = text.replace("\n", ", ").replace("\r", "")
    parts = re.split(r"[;,]", text)
    result: list[str] = []
    for part in parts:
        result.extend(_split_on_and(part.strip()))
    return [p.strip() for p in result if len(p.strip()) > 4]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_request(user_input: str) -> list[Task]:
    """Parse a natural-language pet-care request into a list of Task objects.

    Operates entirely in demo mode (no LLM, no network).
    Returns an empty list for blank or unparseable input.

    Future LLM hook: replace the segment loop body with a structured
    extraction call (e.g. Claude tool-use) while keeping the same return type.
    """
    if not user_input.strip():
        return []

    segments = _split_segments(user_input)
    tasks: list[Task] = []

    for segment in segments:
        task_type = _detect_task_type(segment)
        duration = _extract_duration(segment) or _DEFAULT_DURATIONS.get(task_type, 15)
        due_time = _extract_time(segment)
        priority = _PRIORITY_BY_TYPE.get(task_type, 1)
        title = _build_title(segment, task_type)

        if not title:
            continue

        tasks.append(Task(
            title=title,
            task_type=task_type,
            duration=duration,
            priority=priority,
            recurring=False,
            due_time=due_time,
        ))

    logger.info(
        "Parsed %d task(s) from input (demo mode) | snippet='%s'",
        len(tasks), user_input[:60],
    )
    return tasks
