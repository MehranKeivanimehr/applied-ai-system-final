import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from pawpal_system import Task, TaskStatus, Pet, Owner, Scheduler


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_task(title="Walk", duration=30, priority=2,
              due_time="09:00", due_date="2026-03-29",
              frequency=None, recurring=False,
              status=TaskStatus.PENDING):
    t = Task(title=title, task_type="exercise", duration=duration,
             priority=priority, recurring=recurring,
             due_time=due_time, due_date=due_date,
             frequency=frequency)
    t.status = status
    return t


@pytest.fixture
def owner():
    o = Owner(name="Alex", available_time=60)
    pet = Pet(name="Buddy", species="Dog", age=3, notes="")
    o.add_pet(pet)
    return o


@pytest.fixture
def buddy(owner):
    return owner.pets[0]


@pytest.fixture
def scheduler(owner):
    return Scheduler(owner)


# ---------------------------------------------------------------------------
# Existing tests (kept)
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status():
    task = Task(title="Feed", task_type="feeding", duration=10, priority=2, recurring=True)
    assert task.status == TaskStatus.PENDING
    task.mark_complete()
    assert task.status == TaskStatus.COMPLETE


def test_add_task_increases_pet_task_count():
    pet = Pet(name="Buddy", species="Dog", age=3, notes="Energetic")
    task = Task(title="Walk", task_type="exercise", duration=30, priority=3, recurring=True)
    assert len(pet.get_tasks()) == 0
    pet.add_task(task)
    assert len(pet.get_tasks()) == 1


# ---------------------------------------------------------------------------
# 1. Sorting by time
# ---------------------------------------------------------------------------

def test_sort_by_time_orders_ascending(owner, buddy):
    t1 = make_task(title="Lunch",    due_time="14:00")
    t2 = make_task(title="Breakfast",due_time="08:00")
    t3 = make_task(title="Walk",     due_time="10:00")
    for t in (t1, t2, t3):
        buddy.add_task(t)

    result = Scheduler(owner).sort_by_time()
    assert [t.due_time for t in result] == ["08:00", "10:00", "14:00"]


def test_sort_by_time_no_time_goes_last(owner, buddy):
    timed   = make_task(title="Walk",  due_time="07:00")
    untimed = make_task(title="Groom", due_time=None)
    buddy.add_task(timed)
    buddy.add_task(untimed)

    result = Scheduler(owner).sort_by_time()
    assert result[-1].title == "Groom"


def test_sort_by_time_single_task(owner, buddy):
    buddy.add_task(make_task())
    assert len(Scheduler(owner).sort_by_time()) == 1


def test_sort_by_time_no_tasks(owner):
    assert Scheduler(owner).sort_by_time() == []


# ---------------------------------------------------------------------------
# 2. Filtering by pet name and status
# ---------------------------------------------------------------------------

def test_filter_by_pet_name():
    o = Owner(name="Alex", available_time=60)
    buddy = Pet(name="Buddy", species="Dog", age=3, notes="")
    luna  = Pet(name="Luna",  species="Cat", age=2, notes="")
    buddy.add_task(make_task(title="Walk"))
    luna.add_task(make_task(title="Brush"))
    o.add_pet(buddy)
    o.add_pet(luna)

    result = o.view_tasks(pet_name="Buddy")
    assert len(result) == 1
    assert result[0].title == "Walk"


def test_filter_by_status_pending(owner, buddy):
    buddy.add_task(make_task(title="Walk",  status=TaskStatus.PENDING))
    buddy.add_task(make_task(title="Bath",  status=TaskStatus.COMPLETE))

    result = owner.view_tasks(status=TaskStatus.PENDING)
    assert all(t.status == TaskStatus.PENDING for t in result)
    assert len(result) == 1


def test_filter_by_pet_and_status():
    o = Owner(name="Alex", available_time=60)
    luna = Pet(name="Luna", species="Cat", age=2, notes="")
    luna.add_task(make_task(title="Feed",  status=TaskStatus.PENDING))
    luna.add_task(make_task(title="Brush", status=TaskStatus.COMPLETE))
    o.add_pet(luna)

    result = o.view_tasks(pet_name="Luna", status=TaskStatus.COMPLETE)
    assert len(result) == 1
    assert result[0].title == "Brush"


def test_filter_no_pets():
    o = Owner(name="Alex", available_time=60)
    assert o.view_tasks() == []


def test_filter_nonexistent_pet_name(owner):
    assert owner.view_tasks(pet_name="Ghost") == []


def test_filter_pet_no_tasks(owner):
    assert owner.view_tasks(pet_name="Buddy") == []


# ---------------------------------------------------------------------------
# 3. Recurring task creation
# ---------------------------------------------------------------------------

def test_daily_recurring_creates_next_task(buddy):
    o = Owner(name="Alex", available_time=60)
    o.add_pet(buddy)
    task = make_task(title="Feed", frequency="daily", recurring=True,
                     due_date="2026-03-29")
    buddy.add_task(task)

    next_task = Scheduler(o).mark_task_complete(task, buddy)
    assert next_task is not None
    assert next_task.due_date == "2026-03-30"


def test_weekly_recurring_creates_next_task(buddy):
    o = Owner(name="Alex", available_time=60)
    o.add_pet(buddy)
    task = make_task(title="Bath", frequency="weekly", recurring=True,
                     due_date="2026-03-29")
    buddy.add_task(task)

    next_task = Scheduler(o).mark_task_complete(task, buddy)
    assert next_task.due_date == "2026-04-05"


def test_non_recurring_returns_none(buddy):
    o = Owner(name="Alex", available_time=60)
    o.add_pet(buddy)
    task = make_task(title="Walk", frequency=None, recurring=False)
    buddy.add_task(task)
    original_count = len(buddy.tasks)

    result = Scheduler(o).mark_task_complete(task, buddy)
    assert result is None
    assert len(buddy.tasks) == original_count


def test_recurring_original_marked_complete(buddy):
    o = Owner(name="Alex", available_time=60)
    o.add_pet(buddy)
    task = make_task(frequency="daily", recurring=True)
    buddy.add_task(task)

    Scheduler(o).mark_task_complete(task, buddy)
    assert task.status == TaskStatus.COMPLETE


def test_recurring_next_task_is_pending(buddy):
    o = Owner(name="Alex", available_time=60)
    o.add_pet(buddy)
    task = make_task(frequency="daily", recurring=True, due_date="2026-03-29")
    buddy.add_task(task)

    next_task = Scheduler(o).mark_task_complete(task, buddy)
    assert next_task.status == TaskStatus.PENDING


def test_recurring_inherits_time_and_duration(buddy):
    o = Owner(name="Alex", available_time=60)
    o.add_pet(buddy)
    task = make_task(due_time="08:00", duration=20,
                     frequency="daily", recurring=True, due_date="2026-03-29")
    buddy.add_task(task)

    next_task = Scheduler(o).mark_task_complete(task, buddy)
    assert next_task.due_time == "08:00"
    assert next_task.duration == 20


# ---------------------------------------------------------------------------
# 4. Conflict detection
# ---------------------------------------------------------------------------

def test_exact_same_time_is_conflict():
    a = make_task(title="Walk",  due_time="09:00", duration=30, due_date="2026-03-29")
    b = make_task(title="Bath",  due_time="09:00", duration=30, due_date="2026-03-29")
    assert a.is_conflicting(b) is True


def test_overlapping_windows_is_conflict():
    a = make_task(title="Walk",  due_time="09:00", duration=30, due_date="2026-03-29")
    b = make_task(title="Bath",  due_time="09:15", duration=30, due_date="2026-03-29")
    assert a.is_conflicting(b) is True


def test_adjacent_tasks_not_conflict():
    # A ends at 09:30, B starts at 09:30 — touching but not overlapping
    a = make_task(title="Walk",  due_time="09:00", duration=30, due_date="2026-03-29")
    b = make_task(title="Bath",  due_time="09:30", duration=30, due_date="2026-03-29")
    assert a.is_conflicting(b) is False


def test_no_overlap_not_conflict():
    a = make_task(title="Walk",  due_time="09:00", duration=30, due_date="2026-03-29")
    b = make_task(title="Bath",  due_time="10:00", duration=30, due_date="2026-03-29")
    assert a.is_conflicting(b) is False


def test_different_dates_not_conflict():
    a = make_task(title="Walk", due_time="09:00", duration=30, due_date="2026-03-29")
    b = make_task(title="Bath", due_time="09:00", duration=30, due_date="2026-03-30")
    assert a.is_conflicting(b) is False


def test_missing_due_time_not_conflict():
    a = make_task(title="Walk",  due_time=None,    duration=30)
    b = make_task(title="Bath",  due_time="09:00", duration=30)
    assert a.is_conflicting(b) is False


def test_detect_conflicts_returns_pair(owner, buddy):
    a = make_task(title="Walk", due_time="09:00", duration=30)
    b = make_task(title="Bath", due_time="09:15", duration=30)
    buddy.add_task(a)
    buddy.add_task(b)

    conflicts = Scheduler(owner).detect_conflicts()
    assert len(conflicts) == 1
    titles = {conflicts[0][0].title, conflicts[0][1].title}
    assert titles == {"Walk", "Bath"}


def test_detect_conflicts_empty_when_none(owner, buddy):
    a = make_task(title="Walk",  due_time="09:00", duration=30)
    b = make_task(title="Bath",  due_time="10:00", duration=30)
    buddy.add_task(a)
    buddy.add_task(b)

    assert Scheduler(owner).detect_conflicts() == []


def test_warn_conflicts_message_format(owner, buddy):
    a = make_task(title="Walk", due_time="09:00", duration=30)
    b = make_task(title="Bath", due_time="09:00", duration=30)
    buddy.add_task(a)
    buddy.add_task(b)

    warnings = Scheduler(owner).warn_conflicts()
    assert len(warnings) == 1
    assert "WARNING" in warnings[0]


# ---------------------------------------------------------------------------
# 5. Daily plan generation
# ---------------------------------------------------------------------------

def test_daily_plan_fits_within_time(owner, buddy):
    for title in ("Walk", "Feed", "Groom"):
        buddy.add_task(make_task(title=title, duration=20))

    plan = Scheduler(owner).generate_daily_plan()
    assert len(plan) == 3


def test_daily_plan_excludes_task_over_time(owner, buddy):
    # priority 3 = 50 min fits, leaves 10 min — priority 1 = 20 min does not fit
    buddy.add_task(make_task(title="BigWalk", duration=50, priority=3))
    buddy.add_task(make_task(title="Feed",    duration=20, priority=1))

    plan = Scheduler(owner).generate_daily_plan()
    titles = [t.title for t in plan]
    assert "BigWalk" in titles
    assert "Feed" not in titles


def test_daily_plan_skips_complete_tasks(owner, buddy):
    buddy.add_task(make_task(title="Done",    status=TaskStatus.COMPLETE))
    buddy.add_task(make_task(title="Pending", status=TaskStatus.PENDING))

    plan = Scheduler(owner).generate_daily_plan()
    assert len(plan) == 1
    assert plan[0].title == "Pending"


def test_daily_plan_skips_skipped_tasks(owner, buddy):
    buddy.add_task(make_task(title="Skipped", status=TaskStatus.SKIPPED))

    plan = Scheduler(owner).generate_daily_plan()
    assert plan == []


def test_daily_plan_no_tasks(owner):
    assert Scheduler(owner).generate_daily_plan() == []


def test_daily_plan_no_available_time(buddy):
    o = Owner(name="Alex", available_time=0)
    o.add_pet(buddy)
    buddy.add_task(make_task(duration=10))

    assert Scheduler(o).generate_daily_plan() == []


def test_daily_plan_priority_ordering(owner, buddy):
    low  = make_task(title="Low",  priority=1, due_time="09:00", duration=10)
    high = make_task(title="High", priority=5, due_time="09:00", duration=10)
    buddy.add_task(low)
    buddy.add_task(high)

    plan = Scheduler(owner).generate_daily_plan()
    assert plan[0].title == "High"
