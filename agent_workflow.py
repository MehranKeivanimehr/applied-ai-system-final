"""
agent_workflow.py — Observable multi-step SafeCare AI workflow.

Exposes a single entry point, run_safecare_workflow(), that executes the
full AI pipeline and returns a structured result including visible
intermediate steps.  No hidden chain-of-thought; each step shows only
its operational status and a short factual message.

All computation is offline and deterministic — no external APIs required.
"""
from __future__ import annotations

from guardrails import check_safety
from knowledge_base import retrieve_guidance
from ai_parser import parse_request
from safecare_logger import get_logger

logger = get_logger("agent_workflow")

# Valid task types produced by ai_parser
_VALID_TASK_TYPES = {"exercise", "feeding", "medication", "grooming", "enrichment", "vet", "other"}


def _step(name: str, status: str, message: str) -> dict:
    """Return a workflow step record."""
    return {"step_name": name, "status": status, "message": message}


def run_safecare_workflow(user_input: str, species: str = "dog") -> dict:
    """Run the full SafeCare AI pipeline and return an observable result dict.

    Parameters
    ----------
    user_input : str
        Free-text pet-care request from the user.
    species : str
        Pet species (e.g. 'dog', 'cat', 'rabbit').  Used by the guardrails
        and retrieval modules for species-specific logic.

    Returns
    -------
    dict with keys:
        final_status      – 'safe' | 'warning' | 'blocked'
        warnings          – list[str] of safety warning messages
        retrieved_guidance – list[dict] of matched knowledge entries
        parsed_tasks      – list[Task] produced by the parser
        steps             – list[dict], each with step_name/status/message
    """
    steps: list[dict] = []
    logger.info(
        "Workflow started | species=%s | input_len=%d | snippet='%s'",
        species, len(user_input), user_input[:60],
    )

    # ------------------------------------------------------------------
    # Step 1: Inspect user request
    # ------------------------------------------------------------------
    if not user_input.strip():
        steps.append(_step(
            "Inspect user request", "blocked",
            "Input is empty — nothing to process.",
        ))
        logger.warning("Workflow aborted: empty input")
        return {
            "final_status": "blocked",
            "warnings": ["Input is empty. Please describe your pet's care needs."],
            "retrieved_guidance": [],
            "parsed_tasks": [],
            "steps": steps,
        }

    word_count = len(user_input.split())
    steps.append(_step(
        "Inspect user request", "ok",
        f"Received {word_count} word(s) for species='{species}'.",
    ))

    # ------------------------------------------------------------------
    # Step 2: Run safety guardrails
    # ------------------------------------------------------------------
    safety = check_safety(user_input, pet_species=species)

    if safety.blocked:
        steps.append(_step(
            "Run safety guardrails", "blocked",
            f"{len(safety.warnings)} safety issue(s) detected — request blocked.",
        ))
        logger.warning(
            "Workflow blocked at guardrails | issues=%d", len(safety.warnings)
        )
        return {
            "final_status": "blocked",
            "warnings": safety.warnings,
            "retrieved_guidance": [],
            "parsed_tasks": [],
            "steps": steps,
        }
    elif safety.warnings:
        steps.append(_step(
            "Run safety guardrails", "warning",
            f"{len(safety.warnings)} advisory warning(s) — proceeding with caution.",
        ))
    else:
        steps.append(_step(
            "Run safety guardrails", "ok",
            "No safety issues detected.",
        ))

    # ------------------------------------------------------------------
    # Step 3: Retrieve local pet-care guidance
    # ------------------------------------------------------------------
    guidance = retrieve_guidance(user_input, species=species)
    steps.append(_step(
        "Retrieve local pet-care guidance", "ok",
        f"Retrieved {len(guidance)} relevant knowledge entry(s) from local base.",
    ))

    # ------------------------------------------------------------------
    # Step 4: Parse natural-language request into structured tasks
    # ------------------------------------------------------------------
    tasks = parse_request(user_input)
    steps.append(_step(
        "Parse natural-language request into structured tasks", "ok",
        f"Extracted {len(tasks)} task(s) from input.",
    ))

    # ------------------------------------------------------------------
    # Step 5: Validate parsed tasks
    # ------------------------------------------------------------------
    invalid = [t for t in tasks if t.task_type not in _VALID_TASK_TYPES or t.duration <= 0]
    if invalid:
        steps.append(_step(
            "Validate parsed tasks", "warning",
            f"{len(invalid)} task(s) have unexpected attributes and were flagged.",
        ))
    else:
        n = len(tasks)
        msg = f"All {n} task(s) passed validation." if n > 0 else "No tasks to validate."
        steps.append(_step("Validate parsed tasks", "ok", msg))

    # ------------------------------------------------------------------
    # Step 6: Prepare output for scheduler
    # ------------------------------------------------------------------
    if tasks:
        steps.append(_step(
            "Prepare output for scheduler", "ok",
            f"{len(tasks)} task(s) ready for the PawPal+ scheduler.",
        ))
    else:
        steps.append(_step(
            "Prepare output for scheduler", "warning",
            "No tasks were extracted — consider rephrasing the request.",
        ))

    final_status = "warning" if safety.warnings else "safe"
    logger.info(
        "Workflow complete | final_status=%s | tasks=%d | guidance=%d",
        final_status, len(tasks), len(guidance),
    )
    return {
        "final_status": final_status,
        "warnings": safety.warnings,
        "retrieved_guidance": guidance,
        "parsed_tasks": tasks,
        "steps": steps,
    }
