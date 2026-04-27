import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agent_workflow import run_safecare_workflow

# ---------------------------------------------------------------------------
# Expected step sequence for a normal safe request that finds guidance and
# extracts at least one task.  Blocked and retry paths have different sequences.
# ---------------------------------------------------------------------------
_EXPECTED_STEP_NAMES = [
    "Inspect user request",
    "Run safety guardrails",
    "Retrieve local pet-care guidance",
    "Parse natural-language request into structured tasks",
    "Validate parsed tasks",
    "Decision: Parser confidence",
    "Decision: Ready for scheduler",
]

# Step names present in every blocked response
_BLOCKED_CORE_STEPS = [
    "Inspect user request",
    "Run safety guardrails",
    "Decision: Stop workflow",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_names(result: dict) -> list[str]:
    return [s["step_name"] for s in result["steps"]]


def _step_statuses(result: dict) -> dict[str, str]:
    return {s["step_name"]: s["status"] for s in result["steps"]}


def _decision_steps(result: dict) -> list[dict]:
    return [s for s in result["steps"] if s["step_name"].startswith("Decision:")]


# ---------------------------------------------------------------------------
# 1. Return type and structure
# ---------------------------------------------------------------------------

def test_returns_dict():
    result = run_safecare_workflow("walk the dog at 8am")
    assert isinstance(result, dict)


def test_result_has_required_keys():
    result = run_safecare_workflow("walk the dog at 8am")
    required = {"final_status", "warnings", "retrieved_guidance", "parsed_tasks", "steps",
                "parser_confidence"}
    assert required <= result.keys()


def test_steps_is_list():
    result = run_safecare_workflow("walk the dog")
    assert isinstance(result["steps"], list)


def test_each_step_has_required_fields():
    result = run_safecare_workflow("walk the dog")
    for step in result["steps"]:
        assert "step_name" in step
        assert "status" in step
        assert "message" in step


def test_parser_confidence_key_always_present():
    for text in ["walk at 8am", "", "Give chocolate to the dog"]:
        result = run_safecare_workflow(text, species="dog")
        assert "parser_confidence" in result


def test_parser_confidence_valid_label():
    for text in ["walk at 8am", "Help my pet.", "Give chocolate to the dog"]:
        result = run_safecare_workflow(text, species="dog")
        assert result["parser_confidence"] in {"high", "medium", "low"}


# ---------------------------------------------------------------------------
# 2. Safe request
# ---------------------------------------------------------------------------

def test_safe_request_final_status_is_safe():
    result = run_safecare_workflow("Morning walk for 30 minutes at 8am, feeding at 6pm.")
    assert result["final_status"] == "safe"


def test_safe_request_warnings_empty():
    result = run_safecare_workflow("Morning walk for 30 minutes.")
    assert result["warnings"] == []


def test_safe_request_tasks_nonempty():
    result = run_safecare_workflow("walk the dog for 30 minutes at 8am, feeding at 6pm")
    assert len(result["parsed_tasks"]) >= 1


def test_safe_request_guidance_nonempty():
    result = run_safecare_workflow("Morning walk and feeding at 8am.")
    assert len(result["retrieved_guidance"]) >= 1


def test_safe_request_includes_all_steps():
    result = run_safecare_workflow("Morning walk at 8am for 30 minutes.")
    assert _step_names(result) == _EXPECTED_STEP_NAMES


def test_safe_request_guardrails_step_ok():
    result = run_safecare_workflow("Feed the cat at 7am.")
    statuses = _step_statuses(result)
    assert statuses["Run safety guardrails"] == "ok"


# ---------------------------------------------------------------------------
# 3. Soft-warning request (dosage)
# ---------------------------------------------------------------------------

def test_dosage_request_final_status_is_warning():
    result = run_safecare_workflow("Give 250mg of antibiotics at 9am.", species="dog")
    assert result["final_status"] == "warning"


def test_dosage_request_not_blocked():
    result = run_safecare_workflow("Give 1 tablet of medication at 9am.", species="dog")
    assert result["final_status"] != "blocked"


def test_dosage_request_has_warnings():
    result = run_safecare_workflow("Give 500mg of medicine at 9am.")
    assert len(result["warnings"]) >= 1


def test_dosage_request_still_produces_tasks():
    result = run_safecare_workflow("Give 1 tablet medication at 9am daily.")
    assert result["final_status"] != "blocked"
    assert len(result["parsed_tasks"]) >= 1


def test_dosage_guardrails_step_is_warning():
    result = run_safecare_workflow("Give 250mg of antibiotics.", species="dog")
    statuses = _step_statuses(result)
    assert statuses["Run safety guardrails"] == "warning"


def test_dosage_request_ready_step_is_warning():
    result = run_safecare_workflow("Give 250mg of antibiotics at 9am.", species="dog")
    statuses = _step_statuses(result)
    assert statuses["Decision: Ready for scheduler"] == "warning"


# ---------------------------------------------------------------------------
# 4. Blocked requests
# ---------------------------------------------------------------------------

def test_toxic_food_returns_blocked():
    result = run_safecare_workflow("Give the dog some chocolate.", species="dog")
    assert result["final_status"] == "blocked"


def test_blocked_request_has_warnings():
    result = run_safecare_workflow("Give Max some grapes.", species="dog")
    assert len(result["warnings"]) >= 1


def test_blocked_request_no_tasks():
    result = run_safecare_workflow("Feed the dog chocolate.", species="dog")
    assert result["parsed_tasks"] == []


def test_blocked_request_no_guidance():
    result = run_safecare_workflow("Give the cat lily flowers.", species="cat")
    assert result["retrieved_guidance"] == []


def test_emergency_returns_blocked():
    result = run_safecare_workflow("My dog is seizing.", species="dog")
    assert result["final_status"] == "blocked"


def test_vet_bypass_returns_blocked():
    result = run_safecare_workflow("I don't need a vet, just give medication at home.")
    assert result["final_status"] == "blocked"


def test_blocked_request_confidence_is_low():
    result = run_safecare_workflow("Give the dog chocolate.", species="dog")
    assert result["parser_confidence"] == "low"


# ---------------------------------------------------------------------------
# 5. Decision node — Stop workflow
# ---------------------------------------------------------------------------

def test_blocked_request_has_decision_stop_step():
    result = run_safecare_workflow("Give the dog chocolate.", species="dog")
    assert "Decision: Stop workflow" in _step_names(result)


def test_blocked_decision_stop_status_is_blocked():
    result = run_safecare_workflow("Give the dog chocolate.", species="dog")
    statuses = _step_statuses(result)
    assert statuses["Decision: Stop workflow"] == "blocked"


def test_blocked_decision_stop_message_mentions_safety():
    result = run_safecare_workflow("Give the dog chocolate.", species="dog")
    stop_step = next(s for s in result["steps"] if s["step_name"] == "Decision: Stop workflow")
    msg = stop_step["message"].lower()
    assert any(word in msg for word in ("unsafe", "guardrail", "safety", "toxic", "stop"))


def test_blocked_workflow_stops_early():
    result = run_safecare_workflow("Give the dog chocolate.", species="dog")
    names = _step_names(result)
    assert "Decision: Stop workflow" in names
    assert "Retrieve local pet-care guidance" not in names
    assert "Parse natural-language request into structured tasks" not in names


def test_blocked_request_has_exactly_one_decision_step():
    result = run_safecare_workflow("Give the dog chocolate.", species="dog")
    assert len(_decision_steps(result)) == 1


def test_emergency_has_decision_stop_step():
    result = run_safecare_workflow("My dog is seizing.", species="dog")
    assert "Decision: Stop workflow" in _step_names(result)


# ---------------------------------------------------------------------------
# 6. Decision node — Parser confidence
# ---------------------------------------------------------------------------

def test_safe_request_includes_parser_confidence_step():
    result = run_safecare_workflow("Morning walk at 8am.")
    assert "Decision: Parser confidence" in _step_names(result)


def test_request_with_explicit_time_confidence_is_high():
    result = run_safecare_workflow("Walk at 8am for 30 minutes.")
    assert result["parser_confidence"] == "high"


def test_high_confidence_step_status_is_ok():
    result = run_safecare_workflow("Walk at 8am for 30 minutes.")
    statuses = _step_statuses(result)
    assert statuses["Decision: Parser confidence"] == "ok"


def test_vague_request_confidence_is_low_or_medium():
    result = run_safecare_workflow("Help my pet feel better.")
    assert result["parser_confidence"] in {"low", "medium"}


def test_vague_request_includes_parser_confidence_step():
    result = run_safecare_workflow("Help my pet feel better.")
    assert "Decision: Parser confidence" in _step_names(result)


def test_medium_or_low_confidence_step_status_is_warning():
    result = run_safecare_workflow("Help my pet feel better.")
    if result["parser_confidence"] in {"medium", "low"}:
        statuses = _step_statuses(result)
        assert statuses["Decision: Parser confidence"] == "warning"


def test_confidence_step_message_contains_label():
    result = run_safecare_workflow("Walk at 8am.")
    conf_step = next(s for s in result["steps"] if s["step_name"] == "Decision: Parser confidence")
    label = result["parser_confidence"]
    assert label in conf_step["message"].lower()


# ---------------------------------------------------------------------------
# 7. Decision node — Ready for scheduler
# ---------------------------------------------------------------------------

def test_safe_request_includes_decision_ready_step():
    result = run_safecare_workflow("Morning walk at 8am for 30 minutes.")
    assert "Decision: Ready for scheduler" in _step_names(result)


def test_safe_request_ready_step_is_ok():
    result = run_safecare_workflow("Morning walk at 8am for 30 minutes.")
    statuses = _step_statuses(result)
    assert statuses["Decision: Ready for scheduler"] == "ok"


def test_vague_request_ready_step_exists():
    # "Help my pet feel better." produces 1 task (type 'other'), so ready step is ok.
    # The ready step is 'warning' only when 0 tasks are extracted.
    result = run_safecare_workflow("Help my pet feel better.")
    assert "Decision: Ready for scheduler" in _step_names(result)


def test_zero_task_request_ready_step_is_warning():
    # "Hi" is 2 chars — too short for the parser's minimum segment length (>4),
    # so 0 tasks are extracted and the ready step signals warning.
    result = run_safecare_workflow("Hi")
    statuses = _step_statuses(result)
    assert statuses["Decision: Ready for scheduler"] == "warning"


def test_ready_step_message_mentions_scheduler():
    result = run_safecare_workflow("Morning walk at 8am.")
    ready_step = next(s for s in result["steps"] if s["step_name"] == "Decision: Ready for scheduler")
    assert "scheduler" in ready_step["message"].lower()


# ---------------------------------------------------------------------------
# 8. Visible decision steps overall
# ---------------------------------------------------------------------------

def test_safe_request_has_two_or_more_decision_steps():
    result = run_safecare_workflow("Morning walk at 8am for 30 minutes.")
    assert len(_decision_steps(result)) >= 2


def test_decision_steps_all_start_with_decision_prefix():
    result = run_safecare_workflow("Morning walk at 8am.")
    for step in _decision_steps(result):
        assert step["step_name"].startswith("Decision:")


def test_blocked_has_fewer_decision_steps_than_safe():
    blocked = run_safecare_workflow("Give the dog chocolate.", species="dog")
    safe = run_safecare_workflow("Morning walk at 8am.")
    assert len(_decision_steps(blocked)) < len(_decision_steps(safe))


# ---------------------------------------------------------------------------
# 9. Empty input
# ---------------------------------------------------------------------------

def test_empty_input_returns_blocked():
    result = run_safecare_workflow("")
    assert result["final_status"] == "blocked"


def test_whitespace_input_returns_blocked():
    result = run_safecare_workflow("   ")
    assert result["final_status"] == "blocked"


def test_empty_input_first_step_is_blocked():
    result = run_safecare_workflow("")
    first = result["steps"][0]
    assert first["status"] == "blocked"


def test_empty_input_confidence_is_low():
    result = run_safecare_workflow("")
    assert result["parser_confidence"] == "low"


# ---------------------------------------------------------------------------
# 10. Step content validation
# ---------------------------------------------------------------------------

def test_inspect_step_mentions_word_count():
    result = run_safecare_workflow("Morning walk for 30 minutes.")
    inspect = next(s for s in result["steps"] if s["step_name"] == "Inspect user request")
    assert any(char.isdigit() for char in inspect["message"])


def test_retrieval_step_mentions_count():
    result = run_safecare_workflow("Morning walk and feeding.")
    retrieval = next(s for s in result["steps"] if "Retrieve" in s["step_name"])
    assert any(char.isdigit() for char in retrieval["message"])


def test_parse_step_mentions_task_count():
    result = run_safecare_workflow("walk at 8am, feeding at 6pm")
    parse_step = next(s for s in result["steps"] if "Parse" in s["step_name"])
    assert any(char.isdigit() for char in parse_step["message"])


# ---------------------------------------------------------------------------
# 11. No external API key required
# ---------------------------------------------------------------------------

def test_workflow_works_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_safecare_workflow("Morning walk at 8am.")
    assert result["final_status"] in {"safe", "warning", "blocked"}


def test_workflow_is_deterministic():
    text = "Walk at 8am for 30 minutes, feed at 6pm."
    result_a = run_safecare_workflow(text, species="dog")
    result_b = run_safecare_workflow(text, species="dog")
    assert result_a["final_status"] == result_b["final_status"]
    assert result_a["parser_confidence"] == result_b["parser_confidence"]
    assert len(result_a["parsed_tasks"]) == len(result_b["parsed_tasks"])
