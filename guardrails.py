import re
from dataclasses import dataclass, field

from safecare_logger import get_logger

logger = get_logger("guardrails")

# ---------------------------------------------------------------------------
# Safety data tables
# ---------------------------------------------------------------------------

# Substances toxic to specific species (lowercase for matching)
_TOXIC: dict[str, list[str]] = {
    "dog": [
        "chocolate", "xylitol", "grapes", "raisins", "onion", "onions",
        "garlic", "macadamia", "avocado", "alcohol", "caffeine", "coffee",
        "aspirin", "ibuprofen", "acetaminophen", "tylenol", "advil",
        "naproxen", "permethrin",
    ],
    "cat": [
        "lily", "lilies", "xylitol", "onion", "onions", "garlic", "alcohol",
        "caffeine", "coffee", "aspirin", "ibuprofen", "acetaminophen",
        "tylenol", "permethrin", "dog flea",
    ],
    "rabbit": [
        "chocolate", "avocado", "onion", "onions", "garlic", "rhubarb",
        "iceberg lettuce", "potato", "potatoes",
    ],
}

# Symptoms / phrases that indicate a possible emergency
_EMERGENCY_PHRASES: list[str] = [
    "not breathing", "cant breathe", "can't breathe", "difficulty breathing",
    "labored breathing", "seizure", "seizing", "convulsing", "convulsion",
    "collapsed", "collapse", "unresponsive", "unconscious", "not moving",
    "limp body", "bleeding heavily", "bleeding a lot", "lots of blood",
    "blue gums", "pale gums", "white gums", "extreme pain", "crying in pain",
    "suspected poisoning", "poisoned", "ingested", "swallowed something",
    "broken bone", "can't stand", "cannot stand", "not eating for days",
    "hasn't eaten in",
]

# Regex: any specific numeric dosage (e.g. "2 tablets", "500 mg", "3 ml")
_DOSAGE_RE = re.compile(
    r"\b\d+\s*(?:mg|ml|cc|g\b|gram|milligram|tablet|tablets|pill|pills|"
    r"capsule|capsules|dose|doses|drop|drops|unit|units)\b",
    re.IGNORECASE,
)

# Phrases that try to bypass veterinary advice
_VET_BYPASS: list[str] = [
    "instead of the vet", "instead of a vet", "instead of going to the vet",
    "don't need the vet", "don't need a vet", "no need for a vet",
    "avoid the vet", "skip the vet", "replace the vet", "replace my vet",
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class SafetyResult:
    blocked: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def safe_to_proceed(self) -> bool:
        return not self.blocked


def check_safety(user_input: str, pet_species: str = "dog") -> SafetyResult:
    """Scan *user_input* for unsafe content and return a SafetyResult.

    Hard blocks: toxic substances, emergency symptoms, vet-bypass language.
    Soft warnings (not blocked): specific numeric dosages — we schedule the
    reminder but tell the owner to confirm amounts with their vet.
    """
    text = user_input.lower()
    warnings: list[str] = []
    blocked = False

    # --- 1. Toxic substances -------------------------------------------------
    species_toxics: set[str] = set(_TOXIC.get(pet_species.lower(), []))
    # Also include dog toxics as a conservative baseline for unknown species
    if pet_species.lower() not in _TOXIC:
        species_toxics |= set(_TOXIC["dog"])

    for item in species_toxics:
        if item in text:
            warnings.append(
                f"SAFETY BLOCK: '{item}' is toxic to {pet_species}s. "
                f"Do not give this to your pet. Contact a vet immediately "
                f"if your pet has already ingested it."
            )
            blocked = True

    # --- 2. Emergency symptoms -----------------------------------------------
    for phrase in _EMERGENCY_PHRASES:
        if phrase in text:
            warnings.append(
                f"EMERGENCY WARNING: '{phrase}' detected. This may indicate "
                f"a medical emergency. Contact your veterinarian or an "
                f"emergency animal clinic immediately — do not wait."
            )
            blocked = True

    # --- 3. Specific dosage amounts (soft warning — do not block) ------------
    dosage_hits = _DOSAGE_RE.findall(user_input)
    if dosage_hits:
        joined = ", ".join(dosage_hits)
        warnings.append(
            f"VET REQUIRED: Specific dosage mentioned ({joined}). "
            f"PawPal+ can schedule medication reminders, but dosage amounts "
            f"must always be confirmed with your veterinarian before use."
        )
        # intentionally NOT setting blocked = True

    # --- 4. Vet-bypass language ----------------------------------------------
    for phrase in _VET_BYPASS:
        if phrase in text:
            warnings.append(
                "GUARDRAIL: PawPal+ cannot replace professional veterinary "
                "advice. Please consult your vet for medical decisions."
            )
            blocked = True
            break  # one message is enough for this category

    if warnings:
        logger.warning(
            "Safety check triggered | blocked=%s | pet_species=%s | "
            "issues=%d | input_snippet='%s'",
            blocked, pet_species, len(warnings), user_input[:60],
        )
    else:
        logger.info(
            "Safety check passed | pet_species=%s | input_snippet='%s'",
            pet_species, user_input[:60],
        )

    return SafetyResult(blocked=blocked, warnings=warnings)
