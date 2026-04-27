import json
import os
from typing import Optional

from safecare_logger import get_logger

logger = get_logger("knowledge_base")

_KNOWLEDGE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "pet_care_knowledge.json"
)

# ---------------------------------------------------------------------------
# Risk-aware boost groups (RAG enhancement)
# Each set is a semantic risk/topic cluster.  When the query and an entry
# both contain tokens from the same group the entry receives an extra boost,
# surfacing the most contextually relevant guidance even when raw keyword
# overlap is modest.  The boost is only applied after a base keyword score
# has already been established (score > 0 gate).
# ---------------------------------------------------------------------------
_RISK_GROUPS: list[set[str]] = [
    # Toxic / poisonous substances
    {"toxic", "poison", "poisonous", "dangerous", "harmful", "safe",
     "chocolate", "xylitol", "grapes", "raisins", "onion", "garlic",
     "lily", "avocado", "macadamia", "aspirin", "ibuprofen"},
    # Medication / treatment
    {"medication", "medicine", "med", "meds", "drug", "dose", "dosage",
     "prescription", "treatment", "pill", "pills", "tablet", "tablets",
     "capsule", "supplement", "vitamin"},
    # Emergency / acute medical
    {"emergency", "sick", "illness", "vomit", "vomiting", "seizure",
     "collapse", "breathing", "unconscious", "bleeding", "pain", "urgent"},
    # Feeding / nutrition / hydration
    {"feed", "feeding", "food", "meal", "meals", "diet", "nutrition",
     "kibble", "water", "drink", "hydration", "appetite"},
    # Exercise / physical activity
    {"walk", "walking", "run", "running", "exercise", "activity",
     "outdoor", "jog", "hike", "play outside"},
    # Grooming / hygiene
    {"groom", "grooming", "brush", "brushing", "bath", "bathe",
     "nail", "nails", "trim", "clip", "coat", "fur"},
    # Mental enrichment / play
    {"play", "playing", "toy", "toys", "enrich", "enrichment",
     "training", "train", "puzzle", "stimulation"},
]


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

        # All subsequent bonuses are gated on score > 0 so entries with zero
        # keyword relevance are never promoted into the results.
        if score > 0:
            # Species-specific entry preferred over generic 'all'.
            if species.lower() in entry_species:
                score += 0.25

            # Risk-aware boost (RAG enhancement): if both the query and the
            # entry share tokens from the same semantic risk/topic cluster,
            # reward the entry with a coherence bonus (+0.4, max one group).
            for group in _RISK_GROUPS:
                if query_tokens & group and entry_keywords & group:
                    score += 0.4
                    break

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = [entry for _, entry in scored[:top_k]]

    logger.info(
        "Retrieval | query='%s' | species=%s | matched=%d / eligible=%d",
        query[:50], species, len(results), len(scored),
    )
    return results
