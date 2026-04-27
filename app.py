import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, TaskStatus

# --- SafeCare AI modules (graceful fallback if missing) ---
try:
    from agent_workflow import run_safecare_workflow
    from safecare_logger import get_logger
    _AI_AVAILABLE = True
    _log = get_logger("app")
except ImportError as _err:
    _AI_AVAILABLE = False

DATA_FILE = "data.json"

# --- Session State Init: load from file or create fresh ---
if "owner" not in st.session_state:
    loaded = Owner.load_from_json(DATA_FILE)
    st.session_state.owner = loaded if loaded else Owner(name="", available_time=90, preferences={})

if "active_pet" not in st.session_state:
    st.session_state.active_pet = None

if "ai_result" not in st.session_state:
    st.session_state.ai_result = None


def save() -> None:
    """Save current owner state to data.json."""
    st.session_state.owner.save_to_json(DATA_FILE)


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# --- Section 1: Owner Setup ---
st.subheader("Owner Setup")

owner_name = st.text_input("Your name", value=st.session_state.owner.name)
available_time = st.number_input(
    "Available time today (minutes)", min_value=10, max_value=480,
    value=st.session_state.owner.available_time
)

if st.button("Save Owner"):
    st.session_state.owner.name = owner_name
    st.session_state.owner.available_time = available_time
    save()
    st.success(f"Owner '{owner_name}' saved with {available_time} min available.")

st.divider()

# --- Section 2: Add a Pet ---
st.subheader("Add a Pet")

pet_name = st.text_input("Pet name")
species = st.selectbox("Species", ["dog", "cat", "rabbit", "other"])
age = st.number_input("Age (years)", min_value=0, max_value=30, value=1)
notes = st.text_input("Notes (optional)", value="")

if st.button("Add Pet"):
    if pet_name.strip() == "":
        st.warning("Please enter a pet name.")
    else:
        new_pet = Pet(name=pet_name, species=species, age=age, notes=notes)
        st.session_state.owner.add_pet(new_pet)
        st.session_state.active_pet = new_pet
        save()
        st.success(f"'{pet_name}' added.")

if st.session_state.owner.pets:
    st.markdown("**Pets on file:**")
    pet_names = [p.name for p in st.session_state.owner.pets]
    selected_name = st.selectbox("Select active pet for task entry", pet_names)
    st.session_state.active_pet = next(
        p for p in st.session_state.owner.pets if p.name == selected_name
    )

st.divider()

# --- Section 3: Add a Task to the Active Pet ---
st.subheader("Add a Task")

if st.session_state.active_pet is None:
    st.info("Add a pet above before scheduling tasks.")
else:
    st.caption(f"Adding tasks to: **{st.session_state.active_pet.name}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.number_input("Priority (1-5)", min_value=1, max_value=5, value=3)

    task_type = st.text_input("Task type (e.g. exercise, feeding, grooming)", value="exercise")
    due_time = st.text_input("Due time (optional, e.g. 08:00)", value="")
    recurring = st.checkbox("Recurring task")

    if st.button("Add Task"):
        new_task = Task(
            title=task_title,
            task_type=task_type,
            duration=int(duration),
            priority=int(priority),
            recurring=recurring,
            due_time=due_time.strip() or None,
        )
        st.session_state.active_pet.add_task(new_task)
        save()
        st.success(f"Task '{task_title}' added to {st.session_state.active_pet.name}.")

    current_tasks = st.session_state.active_pet.get_tasks()
    if current_tasks:
        st.markdown("**Current tasks:**")
        st.table([
            {
                "Title": t.title,
                "Type": t.task_type,
                "Duration (min)": t.duration,
                "Priority": t.priority,
                "Due": t.due_time or "--",
                "Status": t.status.value,
            }
            for t in current_tasks
        ])

st.divider()

# --- Section AI: SafeCare AI Request (Phase 1) ---
st.subheader("🤖 SafeCare AI Request")

if not _AI_AVAILABLE:
    st.warning(
        "AI modules not found. Ensure guardrails.py, knowledge_base.py, "
        "ai_parser.py, and safecare_logger.py are in the project root."
    )
elif st.session_state.active_pet is None:
    st.info("Add and select a pet above before using the AI request feature.")
else:
    pet = st.session_state.active_pet
    st.caption(
        f"Describe care needs for **{pet.name}** in plain English. "
        "The system will extract tasks, retrieve relevant guidance, and check for safety."
    )

    ai_input = st.text_area(
        "Describe care needs",
        placeholder=(
            "e.g. 'Max needs a morning walk at 8am for 30 minutes, "
            "evening feeding at 6pm, and heart medication at 9am and 9pm'"
        ),
        height=110,
        key="ai_input_field",
    )

    if st.button("🔍 Analyze Request"):
        raw = ai_input.strip()
        if not raw:
            st.warning("Please enter a care request before analyzing.")
        else:
            _log.info(
                "AI request submitted | pet='%s' species='%s' | input='%s'",
                pet.name, pet.species, raw[:80],
            )
            wf = run_safecare_workflow(raw, species=pet.species)
            st.session_state.ai_result = {
                "final_status": wf["final_status"],
                "warnings": wf["warnings"],
                "knowledge": wf["retrieved_guidance"],
                "tasks": wf["parsed_tasks"],
                "steps": wf["steps"],
                "pet_name": pet.name,
                "parser_confidence": wf.get("parser_confidence", "medium"),
            }

    result = st.session_state.ai_result
    if result is not None and result.get("pet_name") == pet.name:
        blocked = result["final_status"] == "blocked"

        # Safety warnings
        for w in result["warnings"]:
            if "SAFETY BLOCK" in w or "EMERGENCY" in w or "GUARDRAIL" in w:
                st.error(w)
            else:
                st.warning(w)

        if blocked:
            st.error(
                "⛔ This request has been blocked by SafeCare guardrails. "
                "Please revise your request or consult a veterinarian."
            )
        else:
            # Knowledge snippets
            if result["knowledge"]:
                with st.expander("📚 Relevant Pet Care Guidance (click to expand)"):
                    for entry in result["knowledge"]:
                        st.markdown(f"**{entry['title']}**")
                        st.markdown(entry["guidance"])
                        st.divider()

            # Parsed tasks preview
            _CONF_BADGE = {"high": "🟢 High", "medium": "🟡 Medium", "low": "🔴 Low"}
            tasks = result["tasks"]
            if tasks:
                conf_label = _CONF_BADGE.get(result.get("parser_confidence", "medium"), "")
                st.markdown(f"**Extracted tasks — review before adding:** &nbsp; Parser confidence: {conf_label}")
                st.table([
                    {
                        "Title": t.title,
                        "Type": t.task_type,
                        "Duration (min)": t.duration,
                        "Priority (1-5)": t.priority,
                        "Due Time": t.due_time or "--",
                    }
                    for t in tasks
                ])

                if st.button(f"✅ Add {len(tasks)} task(s) to {pet.name}"):
                    for t in tasks:
                        pet.add_task(t)
                    save()
                    _log.info(
                        "Added %d AI-parsed tasks to pet '%s'", len(tasks), pet.name
                    )
                    st.success(f"Added {len(tasks)} task(s) to {pet.name}!")
                    st.session_state.ai_result = None
                    st.rerun()
            else:
                st.info(
                    "No tasks could be extracted from this request. "
                    "Try being more specific — include action words like "
                    "'walk', 'feed', 'medication', 'groom', or 'play'."
                )

        # Agent workflow steps expander (always shown after analysis)
        steps = result.get("steps", [])
        if steps:
            _STATUS_ICON = {"ok": "✅", "warning": "⚠️", "blocked": "⛔", "skipped": "⏭️"}
            with st.expander("🔎 Agent workflow steps"):
                for s in steps:
                    icon = _STATUS_ICON.get(s["status"], "•")
                    st.markdown(
                        f"{icon} **{s['step_name']}** — {s['message']}"
                    )

st.divider()

# --- Section 4: Find Next Available Slot ---
st.subheader("Find Next Available Slot")

slot_duration = st.number_input("Task duration to find a slot for (min)", min_value=5, max_value=240, value=30)

if st.button("Find Slot"):
    scheduler = Scheduler(st.session_state.owner)
    slot = scheduler.find_next_available_slot(int(slot_duration))
    if slot:
        st.success(f"Next available slot for a {slot_duration}-min task: **{slot}**")
    else:
        st.warning("No available slot found between 07:00 and 21:00.")

st.divider()

# --- Section 5: Generate Schedule ---
st.subheader("Generate Daily Schedule")

if st.button("Generate Schedule"):
    owner = st.session_state.owner
    if not owner.name:
        st.warning("Please save an owner name first.")
    elif not owner.pets:
        st.warning("Please add at least one pet with tasks.")
    elif not owner.view_tasks():
        st.warning("No tasks found across your pets.")
    else:
        scheduler = Scheduler(owner)
        scheduler.generate_daily_plan()
        explanation = scheduler.explain_plan()
        st.text(explanation)
