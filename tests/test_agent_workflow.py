import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from agent_workflow import run_safecare_workflow

# Expected step names produced by every non-trivial workflow run
_EXPECTED_STEP_NAMES = [
    "Inspect user request",
    "Run safety guardrails",
    "Retrieve local pet-care guidance",
    "Parse natural-language request into structured tasks",
    "Validate parsed tasks",
    "Prepare output for scheduler",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_names(result: dict) -> list[str]:
    return [s["step_name"] for s in result["steps"]]


def _step_statuses(result: dict) -> dict[str, str]:
    return {s["step_name"]: s["status"] for s in result["steps"]}


# ---------------------------------------------------------------------------
# 1. Return type and structure
# ---------------------------------------------------------------------------

def test_returns_dict():
    result = run_safecare_workflow("walk the dog at 8am")
    assert isinstance(result, dict)


def test_result_has_required_keys():
    result = run_safecare_workflow("walk the dog at 8am")
    required = {"final_status", "warnings", "retrieved_guidance", "parsed_tasks", "steps"}
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
    # Not blocked, so tasks should still be parsed
    assert result["final_status"] != "blocked"
    assert len(result["parsed_tasks"]) >= 1


def test_dosage_guardrails_step_is_warning():
    result = run_safecare_workflow("Give 250mg of antibiotics.", species="dog")
    statuses = _step_statuses(result)
    assert statuses["Run safety guardrails"] == "warning"


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


def test_blocked_workflow_stops_early():
    # Blocked workflow should NOT have retrieval/parsing steps
    result = run_safecare_workflow("Give the dog chocolate.", species="dog")
    names = _step_names(result)
    assert "Retrieve local pet-care guidance" not in names
    assert "Parse natural-language request into structured tasks" not in names


# ---------------------------------------------------------------------------
# 5. Empty input
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


# ---------------------------------------------------------------------------
# 6. Step content validation
# ---------------------------------------------------------------------------

def test_inspect_step_mentions_word_count():
    result = run_safecare_workflow("Morning walk for 30 minutes.")
    inspect = next(s for s in result["steps"] if s["step_name"] == "Inspect user request")
    # Message should mention word count or character info
    assert any(char.isdigit() for char in inspect["message"])


def test_retrieval_step_mentions_count():
    result = run_safecare_workflow("Morning walk and feeding.")
    retrieval = next(s for s in result["steps"] if "Retrieve" in s["step_name"])
    assert any(char.isdigit() for char in retrieval["message"])


def test_parse_step_mentions_task_count():
    result = run_safecare_workflow("walk at 8am, feeding at 6pm")
    parse_step = next(
        s for s in result["steps"]
        if "Parse" in s["step_name"]
    )
    assert any(char.isdigit() for char in parse_step["message"])


# ---------------------------------------------------------------------------
# 7. No external API key required
# ---------------------------------------------------------------------------

def test_workflow_works_without_api_key(monkeypatch):
    # Remove any API key env var that might be set
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = run_safecare_workflow("Morning walk at 8am.")
    assert result["final_status"] in {"safe", "warning", "blocked"}
