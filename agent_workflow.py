"""
agent_workflow.py — Observable multi-step SafeCare AI workflow with explicit
decision nodes, retrieval retry, and parser confidence assessment.

Every meaningful choice in the pipeline is surfaced as a named "Decision:"
step so the full reasoning chain is visible without requiring an LLM or any
external API.  All computation is offline and deterministic.
"""
from __future__ import annotations

from guardrails import check_safety
from knowledge_base import retrieve_guidance
from ai_parser import parse_request
from safecare_logger import get_logger

logger = get_logger("agent_workflow")

_VALID_TASK_TYPES = {"exercise", "feeding", "medication", "grooming", "enrichment", "vet", "other"}


def _step(name: str, status: str, message: str) -> dict:
    """Return a workflow step record."""
    return {"step_name": name, "status": status, "message": message}


def _compute_confidence(tasks: list) -> tuple[str, str, str]:
    """Return (label, status, message) representing parser confidence.

    high   — at least one task carries an explicit due_time extracted from the
              user's text (strongest signal of a well-specified request).
    medium — tasks were extracted but none have an explicit due_time; the
              schedule is plausible but the user should confirm times.
    low    — no tasks could be extracted; the parser found no recognisable
              care-related keywords.
    """
    if not tasks:
        return (
            "low",
            "warning",
            "Low confidence — no tasks extracted. Try including action words "
            "like 'walk', 'feed', 'medication', 'groom', or 'play'.",
        )
    if any(t.due_time is not None for t in tasks):
        return (
            "high",
            "ok",
            f"High confidence — {len(tasks)} task(s) extracted with explicit "
            "scheduling information (due time present).",
        )
    return (
        "medium",
        "warning",
        f"Medium confidence — {len(tasks)} task(s) extracted but no explicit "
        "times were found. Review and confirm the schedule before adding.",
    )


def run_safecare_workflow(user_input: str, species: str = "dog") -> dict:
    """Run the full SafeCare AI pipeline and return an observable result dict.

    Parameters
    ----------
    user_input : str
        Free-text pet-care request from the user.
    species : str
        Pet species ('dog', 'cat', 'rabbit', …).  Passed to guardrails and
        retrieval for species-specific logic.

    Returns
    -------
    dict with keys:
        final_status       – 'safe' | 'warning' | 'blocked'
        warnings           – list[str] of safety warning messages
        retrieved_guidance – list[dict] of matched knowledge entries
        parsed_tasks       – list[Task] produced by the parser
        steps              – list[dict], each with step_name/status/message
        parser_confidence  – 'high' | 'medium' | 'low'
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
            "parser_confidence": "low",
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
        # Decision node: make the stopping choice explicit and visible.
        steps.append(_step(
            "Decision: Stop workflow", "blocked",
            "Guardrails detected unsafe content (toxic substance, emergency symptom, "
            "or vet-bypass language). Workflow stopped to protect user and pet safety. "
            "No retrieval, parsing, or scheduling will occur.",
        ))
        logger.warning("Workflow blocked at guardrails | issues=%d", len(safety.warnings))
        return {
            "final_status": "blocked",
            "warnings": safety.warnings,
            "retrieved_guidance": [],
            "parsed_tasks": [],
            "steps": steps,
            "parser_confidence": "low",
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
        f"Retrieved {len(guidance)} entry(s) for species='{species}'.",
    ))

    # Decision node: if species-specific retrieval found nothing, retry
    # with broader species-agnostic matching ('all' sentinel).
    if not guidance:
        steps.append(_step(
            "Decision: Retry retrieval", "warning",
            f"No guidance found for species='{species}'. "
            "Retrying with species-agnostic entries to maximise coverage.",
        ))
        guidance = retrieve_guidance(user_input, species="all")
        if guidance:
            steps.append(_step(
                "Retrieve local pet-care guidance (retry)", "ok",
                f"Broader retrieval found {len(guidance)} general entry(s).",
            ))
        else:
            steps.append(_step(
                "Retrieve local pet-care guidance (retry)", "warning",
                "No guidance entries matched even with broader search. "
                "Proceeding without retrieval context.",
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
        msg = (
            f"All {len(tasks)} task(s) passed validation."
            if tasks else "No tasks to validate."
        )
        steps.append(_step("Validate parsed tasks", "ok", msg))

    # ------------------------------------------------------------------
    # Decision node: parser confidence assessment
    # ------------------------------------------------------------------
    confidence, conf_status, conf_msg = _compute_confidence(tasks)
    steps.append(_step("Decision: Parser confidence", conf_status, conf_msg))

    # ------------------------------------------------------------------
    # Decision node: scheduler readiness
    # ------------------------------------------------------------------
    if tasks:
        sched_status = "warning" if safety.warnings else "ok"
        sched_msg = f"{len(tasks)} task(s) ready for the PawPal+ scheduler."
        if safety.warnings:
            sched_msg += " Advisory warnings apply — review before scheduling."
    else:
        sched_status = "warning"
        sched_msg = (
            "No tasks were extracted. Revise the request or add tasks manually "
            "before scheduling."
        )
    steps.append(_step("Decision: Ready for scheduler", sched_status, sched_msg))

    final_status = "warning" if safety.warnings else "safe"
    logger.info(
        "Workflow complete | final_status=%s | tasks=%d | guidance=%d | confidence=%s",
        final_status, len(tasks), len(guidance), confidence,
    )
    return {
        "final_status": final_status,
        "warnings": safety.warnings,
        "retrieved_guidance": guidance,
        "parsed_tasks": tasks,
        "steps": steps,
        "parser_confidence": confidence,
    }
