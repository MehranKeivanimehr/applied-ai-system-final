import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from ai_parser import (
    parse_request,
    _extract_time,
    _extract_duration,
    _detect_task_type,
)
from pawpal_system import Task


# ---------------------------------------------------------------------------
# 1. parse_request — empty / blank input
# ---------------------------------------------------------------------------

def test_empty_string_returns_empty_list():
    assert parse_request("") == []


def test_whitespace_only_returns_empty_list():
    assert parse_request("   \n  ") == []


# ---------------------------------------------------------------------------
# 2. _extract_time — time parsing
# ---------------------------------------------------------------------------

def test_time_am_lowercase():
    assert _extract_time("walk at 8am") == "08:00"


def test_time_pm_converts_to_24h():
    assert _extract_time("feeding at 6pm") == "18:00"


def test_time_12pm_is_noon():
    assert _extract_time("medication at 12pm") == "12:00"


def test_time_12am_is_midnight():
    assert _extract_time("medication at 12am") == "00:00"


def test_time_with_minutes():
    assert _extract_time("walk at 8:30am") == "08:30"


def test_time_24h_format():
    assert _extract_time("feeding at 14:00") == "14:00"


def test_time_uppercase_am():
    assert _extract_time("walk at 9 AM") == "09:00"


def test_no_time_returns_none():
    assert _extract_time("morning walk for 30 minutes") is None


# ---------------------------------------------------------------------------
# 3. _extract_duration — duration parsing
# ---------------------------------------------------------------------------

def test_duration_minutes_word():
    assert _extract_duration("walk for 30 minutes") == 30


def test_duration_min_abbreviation():
    assert _extract_duration("a 20-min grooming session") == 20


def test_duration_hour():
    assert _extract_duration("1 hour vet appointment") == 60


def test_duration_two_hours():
    assert _extract_duration("2 hour training session") == 120


def test_duration_half_an_hour():
    assert _extract_duration("play for half an hour") == 30


def test_duration_half_a_hour():
    assert _extract_duration("walk for half a hour") == 30


def test_no_duration_returns_none():
    assert _extract_duration("morning walk") is None


# ---------------------------------------------------------------------------
# 4. _detect_task_type — keyword detection
# ---------------------------------------------------------------------------

def test_walk_is_exercise():
    assert _detect_task_type("morning walk in the park") == "exercise"


def test_run_is_exercise():
    assert _detect_task_type("run for 20 minutes") == "exercise"


def test_feed_is_feeding():
    assert _detect_task_type("feed the dog kibble") == "feeding"


def test_meal_is_feeding():
    assert _detect_task_type("evening meal at 6pm") == "feeding"


def test_medication_type():
    assert _detect_task_type("give heart medication") == "medication"


def test_pills_is_medication():
    assert _detect_task_type("give pills at 9am") == "medication"


def test_brush_is_grooming():
    assert _detect_task_type("brush and groom the fur") == "grooming"


def test_bath_is_grooming():
    assert _detect_task_type("bathing session") == "grooming"


def test_play_is_enrichment():
    assert _detect_task_type("play with toys for 20 minutes") == "enrichment"


def test_vet_appointment():
    assert _detect_task_type("vet checkup") == "vet"


def test_unknown_falls_back_to_other():
    assert _detect_task_type("do something vague") == "other"


# ---------------------------------------------------------------------------
# 5. parse_request — Task objects returned
# ---------------------------------------------------------------------------

def test_single_task_returns_one_task():
    tasks = parse_request("walk for 30 minutes at 8am")
    assert len(tasks) == 1


def test_returns_list_of_task_objects():
    tasks = parse_request("feed at 6pm")
    assert all(isinstance(t, Task) for t in tasks)


def test_task_has_correct_type_exercise():
    tasks = parse_request("morning walk at 8am for 30 minutes")
    assert tasks[0].task_type == "exercise"


def test_task_has_correct_type_feeding():
    tasks = parse_request("feeding at 6pm")
    assert tasks[0].task_type == "feeding"


def test_task_has_correct_type_medication():
    tasks = parse_request("heart medication at 9am")
    assert tasks[0].task_type == "medication"


def test_task_due_time_extracted():
    tasks = parse_request("walk at 8am")
    assert tasks[0].due_time == "08:00"


def test_task_duration_extracted():
    tasks = parse_request("walk for 45 minutes")
    assert tasks[0].duration == 45


def test_task_without_time_has_none_due_time():
    tasks = parse_request("daily grooming session")
    assert tasks[0].due_time is None


def test_task_title_is_nonempty_string():
    tasks = parse_request("morning walk at 8am")
    assert isinstance(tasks[0].title, str)
    assert len(tasks[0].title) > 0


def test_task_priority_medication_highest():
    med = parse_request("medication at 9am")[0]
    ex = parse_request("walk at 8am")[0]
    assert med.priority > ex.priority


def test_task_priority_feeding_above_grooming():
    feed = parse_request("feeding at 6pm")[0]
    groom = parse_request("grooming session")[0]
    assert feed.priority >= groom.priority


# ---------------------------------------------------------------------------
# 6. parse_request — multi-task parsing
# ---------------------------------------------------------------------------

def test_two_comma_separated_tasks():
    tasks = parse_request("walk at 8am, feeding at 6pm")
    assert len(tasks) == 2


def test_three_tasks_parsed():
    tasks = parse_request("walk at 8am, feeding at 6pm, medication at 9am")
    assert len(tasks) == 3


def test_task_types_in_multi_task():
    tasks = parse_request("walk at 8am, feeding at 6pm")
    types = {t.task_type for t in tasks}
    assert "exercise" in types
    assert "feeding" in types


def test_semicolon_separator():
    tasks = parse_request("walk for 30 minutes; grooming session for 20 minutes")
    assert len(tasks) == 2


def test_newline_separator():
    tasks = parse_request("walk at 8am\nfeeding at 6pm")
    assert len(tasks) == 2
