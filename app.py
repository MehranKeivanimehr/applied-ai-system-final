import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler, TaskStatus

DATA_FILE = "data.json"

# --- Session State Init: load from file or create fresh ---
if "owner" not in st.session_state:
    loaded = Owner.load_from_json(DATA_FILE)
    st.session_state.owner = loaded if loaded else Owner(name="", available_time=90, preferences={})

if "active_pet" not in st.session_state:
    st.session_state.active_pet = None


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
