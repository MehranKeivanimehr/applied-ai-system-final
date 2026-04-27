from datetime import date

from pawpal_system import Owner, Pet, Task, Scheduler, TaskStatus


def print_task_list(tasks: list[Task], label: str) -> None:
    print(f"\n{label}")
    print("-" * 50)
    if not tasks:
        print("  (no tasks)")
        return
    for i, task in enumerate(tasks, start=1):
        due_time = task.due_time if task.due_time else "no time"
        due_date = task.due_date if task.due_date else "no date"
        print(
            f"  {i}. {task.title:<25} | {due_date}  {due_time:<8} | "
            f"freq: {task.frequency or 'once':<7} | status: {task.status.value}"
        )


def main():
    owner = Owner("Mehran", available_time=90, preferences={"prefers_morning_walks": True})

    dog = Pet(name="Buddy", species="Dog", age=4, notes="Needs exercise")
    cat = Pet(name="Luna", species="Cat", age=2, notes="Takes medication")

    # Tasks added intentionally out of chronological order
    task1 = Task(title="Evening Walk",    task_type="walk",       duration=30, priority=3, recurring=True,  due_time="18:30")
    task2 = Task(title="Feed Buddy",      task_type="feeding",    duration=10, priority=2, recurring=True,  due_time="07:30")
    task3 = Task(title="Give Luna Meds",  task_type="medication", duration=5,  priority=4, recurring=True,  due_time="07:45")
    task4 = Task(title="Playtime",        task_type="enrichment", duration=20, priority=1, recurring=False, due_time="14:00")
    task5 = Task(title="Morning Walk",    task_type="walk",       duration=30, priority=3, recurring=True,  due_time="08:00")
    task6 = Task(title="Brush Luna",      task_type="grooming",   duration=10, priority=2, recurring=False, due_time=None)

    # Intentional conflict pair: Feed Buddy 07:30+10min overlaps Check Buddy Weight 07:35
    task_conflict = Task(title="Check Buddy Weight", task_type="health", duration=15, priority=2, recurring=False, due_time="07:35")

    # Daily recurring task anchored to today so mark_task_complete knows the base date
    task_daily = Task(
        title="Buddy Morning Meds",
        task_type="medication",
        duration=5,
        priority=4,
        recurring=True,
        frequency="daily",
        due_time="08:30",
        due_date=date.today().isoformat(),
    )

    dog.add_task(task1)
    dog.add_task(task2)
    dog.add_task(task5)
    dog.add_task(task_conflict)
    dog.add_task(task_daily)
    cat.add_task(task3)
    cat.add_task(task4)
    cat.add_task(task6)

    owner.add_pet(dog)
    owner.add_pet(cat)

    scheduler = Scheduler(owner)

    # --- Sort by time ---
    print_task_list(scheduler.sort_by_time(), "All tasks sorted by due time (chronological)")

    # --- Filter by pet name ---
    print_task_list(owner.view_tasks(pet_name="Buddy"), "Buddy's tasks only")
    print_task_list(owner.view_tasks(pet_name="Luna"),  "Luna's tasks only")

    # --- Filter by status (all pending before any completions) ---
    print_task_list(owner.view_tasks(status=TaskStatus.PENDING),  "All PENDING tasks")
    print_task_list(owner.view_tasks(status=TaskStatus.COMPLETE), "All COMPLETE tasks (should be empty)")

    # Mark a couple tasks complete, then re-filter
    task2.mark_complete()   # Feed Buddy — done
    task3.mark_complete()   # Give Luna Meds — done

    print_task_list(owner.view_tasks(status=TaskStatus.PENDING),  "PENDING after marking 2 complete")
    print_task_list(owner.view_tasks(status=TaskStatus.COMPLETE), "COMPLETE after marking 2 complete")

    # --- Combined filter: one pet + one status ---
    print_task_list(
        owner.view_tasks(pet_name="Luna", status=TaskStatus.PENDING),
        "Luna's PENDING tasks only"
    )

    # --- Recurring task: mark complete → auto-schedule next day ---
    print(f"\n{'=' * 50}")
    print("Recurring Task Demo")
    print("=" * 50)
    print_task_list(dog.get_tasks(), "Buddy's tasks BEFORE completing daily med")
    next_task = scheduler.mark_task_complete(task_daily, dog)
    print_task_list(dog.get_tasks(), "Buddy's tasks AFTER completing daily med")
    if next_task:
        print(f"\n  --> Next occurrence created: '{next_task.title}' on {next_task.due_date}")

    # --- Conflict detection ---
    print(f"\n{'=' * 40}")
    print("Conflict Check")
    print("=" * 40)
    warnings = scheduler.warn_conflicts()
    if warnings:
        for msg in warnings:
            print(msg)
    else:
        print("No conflicts detected.")

    # --- Daily plan (uses priority sort internally) ---
    scheduler.generate_daily_plan()
    print(f"\n{'=' * 40}")
    print(scheduler.explain_plan())

    # --- Next available slot ---
    print(f"\n{'=' * 40}")
    print("Next Available Slot Demo")
    print("=" * 40)
    for test_duration in [10, 30, 60]:
        slot = scheduler.find_next_available_slot(test_duration)
        if slot:
            print(f"  Next free slot for a {test_duration}-min task: {slot}")
        else:
            print(f"  No available slot found for a {test_duration}-min task (07:00-21:00)")


if __name__ == "__main__":
    main()