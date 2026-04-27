import json
import os
from typing import Optional

from safecare_logger import get_logger

logger = get_logger("knowledge_base")

_KNOWLEDGE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "pet_care_knowledge.json"
)


def load_knowledge() -> list[dict]:
    """Load the local pet-care knowledge base from disk. Returns [] on failure."""
    if not os.path.exists(_KNOWLEDGE_FILE):
        logger.warning("Knowledge file not found: %s", _KNOWLEDGE_FILE)
        return []
    try:
        with open(_KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Knowledge base loaded: %d entries", len(data))
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to load knowledge base: %s", exc)
        return []


def retrieve_guidance(
    query: str, species: str = "dog", top_k: int = 3
) -> list[dict]:
    """Return the top *top_k* knowledge entries most relevant to *query* and *species*.

    Scoring: keyword overlap + partial title-word match bonus.
    Species filter: an entry is eligible if its species list contains the
    requested species or the sentinel value 'all'.
    Returns an empty list for blank queries or when no entries match.
    """
    if not query.strip():
        return []

    entries = load_knowledge()
    if not entries:
        return []

    query_tokens = set(query.lower().split())
    scored: list[tuple[float, dict]] = []

    for entry in entries:
        # Species eligibility check
        entry_species = [s.lower() for s in entry.get("species", ["all"])]
        if "all" not in entry_species and species.lower() not in entry_species:
            continue

        # Primary score: keyword overlap
        entry_keywords = {kw.lower() for kw in entry.get("keywords", [])}
        score: float = len(query_tokens & entry_keywords)

        # Bonus: title word overlap (weighted lower)
        title_tokens = set(entry.get("title", "").lower().split())
        score += len(query_tokens & title_tokens) * 0.5

        # Bonus: species-specific entry preferred over generic 'all'.
        # Only applied when there is already a keyword match so that entries
        # with zero keyword overlap are never promoted past the score > 0 gate.
        if score > 0 and species.lower() in entry_species:
            score += 0.25

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [entry for _, entry in scored[:top_k]]

    logger.info(
        "Retrieval | query='%s' | species=%s | matched=%d / eligible=%d",
        query[:50], species, len(results), len(scored),
    )
    return results
