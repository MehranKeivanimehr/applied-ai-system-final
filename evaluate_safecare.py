"""
evaluate_safecare.py — Reliability evaluation harness for PawPal+ SafeCare AI.

Loads pre-defined test cases from evaluation_cases.json, runs each through
the live SafeCare AI pipeline, and prints a per-case pass/fail result plus
a final summary covering safety accuracy, parser accuracy, and retrieval
keyword accuracy.

Usage:
    python evaluate_safecare.py
"""
import json
import os
import sys

# Allow running from the project root directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from guardrails import check_safety
from knowledge_base import retrieve_guidance
from ai_parser import parse_request

_CASES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation_cases.json")

_COL_WIDTH = 72  # terminal column width for the separator line


def _load_cases() -> list[dict]:
    if not os.path.exists(_CASES_FILE):
        print(f"ERROR: evaluation_cases.json not found at {_CASES_FILE}")
        sys.exit(1)
    with open(_CASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _actual_safety_label(blocked: bool, has_warnings: bool) -> str:
    if blocked:
        return "blocked"
    if has_warnings:
        return "warning"
    return "safe"


def _build_searchable_text(guidance: list[dict], tasks: list) -> str:
    """Concatenate guidance titles/guidance and task titles/types into one text blob."""
    parts: list[str] = []
    for entry in guidance:
        parts.append(entry.get("title", "").lower())
        parts.append(entry.get("guidance", "").lower())
    for task in tasks:
        parts.append(task.title.lower())
        parts.append(task.task_type.lower())
    return " ".join(parts)


def run_evaluation(verbose: bool = True) -> dict:
    """Run all evaluation cases and return a summary dict.

    Parameters
    ----------
    verbose : bool
        Print per-case output when True.
    """
    cases = _load_cases()
    total = len(cases)

    passed = 0
    safety_correct = 0
    parser_correct = 0
    retrieval_correct = 0

    if verbose:
        print("=" * _COL_WIDTH)
        print("  PawPal+ SafeCare AI — Evaluation Harness")
        print("=" * _COL_WIDTH)

    for case in cases:
        case_id = case["id"]
        user_input = case["input"]
        species = case["species"]
        expected_safety = case["expected_safety_result"]
        expected_keywords = case.get("expected_keywords", [])
        expected_min_tasks = case.get("expected_min_tasks", 0)

        # --- Safety check ---------------------------------------------------
        safety = check_safety(user_input, pet_species=species)
        actual_safety = _actual_safety_label(safety.blocked, bool(safety.warnings))
        safety_ok = actual_safety == expected_safety
        if safety_ok:
            safety_correct += 1

        # --- Retrieval and parsing (skipped when blocked) -------------------
        guidance: list[dict] = []
        tasks: list = []
        if not safety.blocked:
            guidance = retrieve_guidance(user_input, species=species)
            tasks = parse_request(user_input)

        # --- Parser check: minimum task count -------------------------------
        parser_ok = len(tasks) >= expected_min_tasks
        if parser_ok:
            parser_correct += 1

        # --- Keyword check: expected words appear in output text ------------
        search_text = _build_searchable_text(guidance, tasks)
        if expected_keywords:
            keywords_ok = all(kw.lower() in search_text for kw in expected_keywords)
        else:
            keywords_ok = True  # no keyword expectation → always passes
        if keywords_ok:
            retrieval_correct += 1

        # --- Case result ----------------------------------------------------
        case_pass = safety_ok and parser_ok and keywords_ok
        if case_pass:
            passed += 1

        if verbose:
            status_tag = "PASS" if case_pass else "FAIL"
            safety_tag = "ok" if safety_ok else f"expected={expected_safety} got={actual_safety}"
            parser_tag = "ok" if parser_ok else f"expected>={expected_min_tasks} got={len(tasks)}"
            kw_tag = "ok" if keywords_ok else f"missing={[k for k in expected_keywords if k.lower() not in search_text]}"
            print(
                f"  [{status_tag}] {case_id:<12} "
                f"safety={safety_tag}  parser={parser_tag}  keywords={kw_tag}"
            )
            if case.get("notes"):
                print(f"         -> {case['notes']}")

    failed = total - passed
    accuracy = passed / total * 100 if total else 0.0
    safety_acc = safety_correct / total * 100 if total else 0.0
    parser_acc = parser_correct / total * 100 if total else 0.0
    retrieval_acc = retrieval_correct / total * 100 if total else 0.0

    if verbose:
        print()
        print("=" * _COL_WIDTH)
        print("  Evaluation Summary")
        print("=" * _COL_WIDTH)
        print(f"  Total cases              : {total}")
        print(f"  Passed                   : {passed}")
        print(f"  Failed                   : {failed}")
        print(f"  Overall accuracy         : {accuracy:.1f}%")
        print(f"  Safety accuracy          : {safety_acc:.1f}%")
        print(f"  Parser accuracy          : {parser_acc:.1f}%")
        print(f"  Retrieval keyword acc.   : {retrieval_acc:.1f}%")
        print("=" * _COL_WIDTH)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "accuracy": accuracy,
        "safety_accuracy": safety_acc,
        "parser_accuracy": parser_acc,
        "retrieval_keyword_accuracy": retrieval_acc,
    }


if __name__ == "__main__":
    run_evaluation(verbose=True)
