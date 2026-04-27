# PawPal+ SafeCare AI

> An offline AI-assisted pet-care planning system that combines natural-language
> request parsing, local knowledge retrieval, safety guardrails, and an observable
> agentic workflow — no API key required.

---

## Original Project

This project was extended from my Module 2 project, **PawPal+**. The original PawPal+ system was a Streamlit-based pet-care scheduler that allowed an owner to add pets, define care tasks, and generate a daily schedule based on task duration, priority, and available owner time.

The original system focused on deterministic scheduling logic, including priority-based planning, task filtering, recurring task handling, conflict detection, and next-available-slot suggestions. For the final applied AI system, I extended this foundation into **PawPal+ SafeCare AI**, which adds natural-language task parsing, local retrieval, safety guardrails, logging, and reliability testing.

## Project Summary

**PawPal+ SafeCare AI** is an offline AI-assisted pet-care planning system. It allows a user to describe pet-care needs in natural language, checks the request for safety risks, retrieves relevant guidance from a local pet-care knowledge base, converts the request into structured tasks, and then uses the existing PawPal+ scheduler to generate a daily care plan.

This project matters because pet-care planning is not only a scheduling problem. Some user requests may involve unsafe foods, emergency symptoms, medication dosage claims, or attempts to avoid veterinary care. The system was therefore designed to combine useful automation with explicit safety boundaries.

## Sample Interactions

### Example 1: Safe care request

**Input**

My dog Max needs a morning walk for 30 minutes, breakfast at 8:00 AM, and playtime for 20 minutes in the evening.

**Expected system behavior**

The system accepts the request, retrieves dog-care guidance, parses the request into structured care tasks, and adds the tasks to the PawPal scheduler. The schedule includes walking, feeding, and playtime tasks, along with an explanation of how the tasks were selected.

### Example 2: Unsafe food request

**Input**

Give Max chocolate as a reward tonight.

**Expected system behavior**

The system blocks the request because chocolate is unsafe for dogs. It displays a safety warning and does not add the task to the schedule.

### Example 3: Medication dosage request

**Input**

Give Max 2 tablets at 9 PM.

**Expected system behavior**

The system shows a medication-related warning because specific dosage instructions should be confirmed by a veterinarian. Depending on the request category, the system may allow scheduling as a reminder while clearly stating that it is not providing medical dosage advice.

## System Architecture

PawPal+ SafeCare AI extends the original pet-care scheduler with an AI-assisted workflow for natural-language care planning. The user enters a free-text request through the Streamlit interface. The request first passes through safety guardrails, which block or warn about unsafe content such as toxic foods, medication dosage advice, or requests that should require veterinary attention.

If the request is safe to continue, the system retrieves relevant guidance from a small local pet-care knowledge base and parses the request into structured pet-care tasks. These structured tasks are then passed to the existing PawPal scheduler, which generates the daily schedule. The final output includes the schedule, explanation, and any relevant warnings. Logging records key actions, and pytest-based tests validate the reliability of the new AI modules.

![System Architecture](assets/system_architecture.png)

The system is organized as a layered workflow. The user interacts with the Streamlit interface, which serves as the main application entry point. The AI layer consists of three main modules: guardrails, retrieval, and natural-language task parsing. These modules transform raw user input into safe, structured scheduling tasks. The deterministic PawPal scheduler then generates the final daily plan. Reliability is supported by logging, automated tests, and user review of the produced output.

## AI System Modules

| Feature | File | Description |
|---|---|---|
| NL Task Parser | `ai_parser.py` | Converts free-text care requests into scheduled tasks |
| Knowledge Retrieval | `knowledge_base.py` | Keyword-matches requests against 25 local pet-care entries |
| Safety Guardrails | `guardrails.py` | Blocks toxic substances, emergencies, and dosage claims |
| Logging | `safecare_logger.py` | Writes all AI actions and warnings to `logs/safecare.log` |
| Knowledge Base | `data/pet_care_knowledge.json` | 25 curated pet-care guidance entries |

### AI Pipeline Data Flow

```
User types natural-language request
        │
        ▼
 guardrails.check_safety()    ← blocks toxic foods, emergencies, vet-bypass
        │ (if safe)
        ▼
 knowledge_base.retrieve_guidance()  ← keyword search over local JSON
        │
        ▼
 ai_parser.parse_request()    ← regex + keyword extraction → Task objects
        │
        ▼
 pawpal_system.Scheduler      ← existing scheduler (unchanged)
        │
        ▼
 logs/safecare.log            ← every action and warning recorded
```

### Guardrail categories

| Category | Response |
|---|---|
| Toxic substance (chocolate, xylitol, grapes, lily …) | Hard block — request rejected |
| Emergency symptoms (seizure, collapse, not breathing …) | Hard block |
| Vet-bypass language ("avoid the vet", "instead of a vet") | Hard block |
| Specific numeric dosage ("250 mg", "2 tablets") | Soft warning — task still scheduled, vet reminder shown |

---
## Design Decisions

PawPal+ SafeCare AI was designed as a layered system instead of a single large AI function. The workflow separates safety checking, knowledge retrieval, natural-language parsing, and deterministic scheduling into different modules. This makes the system easier to test, debug, and explain.

A local knowledge base was used instead of live internet retrieval. This keeps the project reproducible, avoids API-key requirements, and reduces the risk of retrieving unsafe or unreliable information. The trade-off is that the system can only use the curated pet-care guidance included in the repository.

The original PawPal+ scheduler was preserved rather than replaced. The AI layer converts natural-language input into structured tasks, but the final schedule is still produced by the tested deterministic scheduler. This keeps the system more reliable than allowing the AI layer to directly invent a schedule.

## Testing Summary

The final system includes tests for the original PawPal+ scheduler and the new SafeCare AI modules. The original tests verify scheduling behavior such as task completion, task sorting, recurring tasks, conflict detection, filtering, and daily plan generation. The new tests cover guardrails, local knowledge retrieval, and natural-language task parsing.

The strongest part of the project is backend reliability. The scheduler and AI-support modules are tested separately, which makes failures easier to isolate. The main limitation is that the Streamlit UI is not deeply unit-tested, so the user-facing workflow was also checked manually through app screenshots and demo examples.

This project showed that AI reliability improves when the system is decomposed into small, testable components. Guardrails, retrieval, parsing, and scheduling can each be evaluated independently instead of treating the full application as a black box.


## Reliability and Evaluation

The system was evaluated using automated tests, logging, and manual review through Streamlit demo screenshots. Automated tests cover the original PawPal+ scheduler as well as the new SafeCare AI modules: guardrails, local knowledge retrieval, and natural-language task parsing.

The final test suite passed successfully with 146 out of 146 tests passing. The most important reliability checks were whether unsafe inputs were blocked, medication-related requests produced warnings, safe requests were parsed into structured tasks, and the original scheduler still worked after the AI layer was added.

Logging was added through `safecare_logger.py`, which records AI-related actions and warnings in `logs/safecare.log`. This makes the system easier to inspect when a request is blocked, parsed incorrectly, or handled with a warning.

Manual evaluation was also performed using safe and unsafe pet-care requests in the Streamlit app. The system handled normal scheduling requests, blocked toxic-food requests, and warned about medication dosage language. The main limitation is that the UI workflow was manually checked rather than fully automated with browser-based tests.

## Reflection and Ethics

PawPal+ SafeCare AI has several limitations. The system uses a small local knowledge base, so it cannot cover every breed, medical condition, age group, allergy, or emergency scenario. Its natural-language parser is rule-based, which makes it reproducible but also limited when user requests are vague, incomplete, or phrased in unexpected ways. The system may also reflect the limits of the curated guidance included in the repository.

The system could be misused if a user tried to treat it as a replacement for a veterinarian, especially for medication, emergency symptoms, or illness-related decisions. To reduce this risk, the app uses guardrails that block toxic-food requests, emergency-related language, and attempts to avoid veterinary care. Medication dosage language is treated cautiously, and the system reminds users that dosage decisions should be confirmed by a veterinarian.

The most surprising part of reliability testing was that the safest design was not to make the AI more flexible, but to make it more constrained. Breaking the system into guardrails, retrieval, parsing, and deterministic scheduling made it easier to test and easier to trust. The system became more reliable because unsafe inputs were handled before they could become scheduled tasks.

AI tools were used during the project for planning, debugging, test design, and implementation support. One helpful suggestion was to keep the original PawPal+ scheduler unchanged and add the AI functionality as a separate layer around it. This preserved the tested backend logic while still making the system more intelligent. One flawed suggestion was the earlier folder-structure assumption that treated the PawPal+ project as a nested repository. That would have made the final GitHub repo harder to clone and evaluate, so the structure was corrected before continuing.

## Optional Stretch Features

### 1. Evaluation Harness

`evaluation_cases.json` and `evaluate_safecare.py` provide a reproducible reliability harness for the full pipeline.

**11 test cases** cover safe requests, medication dosage warnings, toxic-food blocks, emergency symptom blocks, vet-bypass blocks, vague requests, species-specific retrieval, and multi-task parsing.

Each case specifies:
- `expected_safety_result` — `"safe"`, `"warning"`, or `"blocked"`
- `expected_min_tasks` — minimum task count from the parser
- `expected_keywords` — words that must appear in retrieved guidance or parsed task output

**Run the evaluation:**

```bash
python evaluate_safecare.py
```

**Example output:**

```
========================================================================
  PawPal+ SafeCare AI — Evaluation Harness
========================================================================
  [PASS] case_001     safety=ok  parser=ok  keywords=ok
  [PASS] case_002     safety=ok  parser=ok  keywords=ok
  [PASS] case_003     safety=ok  parser=ok  keywords=ok
  ...
========================================================================
  Evaluation Summary
========================================================================
  Total cases              : 11
  Passed                   : 11
  Failed                   : 0
  Overall accuracy         : 100.0%
  Safety accuracy          : 100.0%
  Parser accuracy          : 100.0%
  Retrieval keyword acc.   : 100.0%
========================================================================
```

---

### 2. Agentic Workflow

`agent_workflow.py` implements an **offline, deterministic agentic workflow** with explicit decision nodes. This is not a fully autonomous LLM agent; it is a structured pipeline where every significant choice is surfaced as a named decision step with a status and explanation, making the full reasoning chain visible to the user.

**Entry point:**

```python
from agent_workflow import run_safecare_workflow
result = run_safecare_workflow("Walk at 8am, feeding at 6pm", species="dog")
```

**Return dict keys:** `final_status`, `warnings`, `retrieved_guidance`, `parsed_tasks`, `steps`, `parser_confidence`

**Workflow steps and decision nodes:**

| Step | Type | What it does |
|---|---|---|
| Inspect user request | Pipeline | Validates non-empty input, reports word count |
| Run safety guardrails | Pipeline | Checks for toxic substances, emergencies, dosages, vet-bypass |
| **Decision: Stop workflow** | **Decision node** | Appears only when guardrails block — makes the stopping choice explicit with a reason |
| Retrieve local pet-care guidance | Pipeline | Keyword + risk-aware search over local knowledge base |
| **Decision: Retry retrieval** | **Decision node** | Fires when first retrieval returns 0 results; retries with species-agnostic entries and reports the outcome |
| Parse natural-language request into structured tasks | Pipeline | Regex + keyword extraction → Task objects |
| Validate parsed tasks | Pipeline | Task type and duration sanity check |
| **Decision: Parser confidence** | **Decision node** | Labels confidence as `high` (explicit times found), `medium` (tasks but no times), or `low` (no tasks extracted); included in the result dict as `parser_confidence` |
| **Decision: Ready for scheduler** | **Decision node** | Final go/no-go for scheduling: `ok` when tasks exist and request is safe, `warning` when tasks exist but advisories apply or no tasks were found |

**What makes this agentic:**
- **Conditional branching** — blocked guardrails halt the pipeline at a visible decision node; the workflow does not continue to retrieval or parsing
- **Retry behavior** — if species-specific retrieval finds nothing, a decision step fires and the system retries with broader matching, reporting both attempts
- **Confidence scoring** — the parser self-assesses its output and communicates certainty to the user before they confirm adding tasks
- **Explicit decision chain** — every decision node emits a step with a named reason, not a silent code branch

In the app, click **"🔎 Agent workflow steps"** after analyzing a request to see each step's name, status icon (✅ / ⚠️ / ⛔), and explanation. Parser confidence (🟢 High / 🟡 Medium / 🔴 Low) also appears above the extracted tasks table.

---

### 3. RAG Enhancement — Species-Aware and Risk-Aware Retrieval

`knowledge_base.py` now applies a **risk-aware coherence boost** on top of keyword overlap scoring.

**How it works:**
- Seven semantic risk/topic clusters are defined (toxic substances, medication, emergency, feeding, exercise, grooming, enrichment).
- If both the query and a knowledge entry share tokens from the same cluster, the entry receives a `+0.4` coherence bonus — surfacing more contextually relevant guidance even when raw keyword overlap is modest.
- The boost is gated on `score > 0` so entries with zero keyword relevance are never promoted.
- Species-specific entries are preferred over generic `"all"` entries when there is already keyword overlap (`+0.25`).

This is entirely deterministic and offline — no embeddings or external services.

---

## Reflection

This project taught me that applied AI systems require more than generating answers. A useful system must also know when to warn the user, when to block unsafe requests, and when to rely on deterministic logic instead of flexible AI behavior.

The most important design lesson was that safety should appear early in the workflow. By placing guardrails before retrieval and parsing, PawPal+ SafeCare AI avoids turning unsafe user requests into scheduled tasks.

The project also showed the value of extending a working system instead of rebuilding from scratch. The original PawPal+ scheduler provided a stable backend, and the SafeCare AI layer made it more natural, explainable, and safety-aware.




## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # only streamlit + pytest — no API keys needed
```

### Run the app

```bash
streamlit run app.py
```

### Run all tests

```bash
python -m pytest tests/ -v
```

The test suite covers the original PawPal+ scheduler and all AI modules
(guardrails, knowledge base, AI parser, and agentic workflow) — 146 tests total.


## Smarter Scheduling

PawPal+ now includes smarter scheduling features to make task planning more useful. Tasks can be sorted by time, filtered by pet name or completion status, and checked for scheduling conflicts. The scheduler can also detect overlapping tasks and return warning messages instead of failing. In addition, recurring tasks can be recreated automatically for the next occurrence when a daily or weekly task is completed.


## Testing PawPal+
The test suite for PawPal+ was written with pytest and is focused on verifying the core backend logic of the system.

Run the tests with:

python -m pytest

The current tests cover:

task completion and task addition
sorting tasks by time
filtering tasks by pet name and completion status
recurring task creation for daily and weekly tasks
conflict detection for overlapping task times
daily plan generation under time and status constraints

These tests include both normal usage cases and edge cases, such as pets with no tasks, missing due times, adjacent tasks that should not conflict, and tasks that exceed the owner’s available time.

Confidence Level: (4/5)

The current confidence level is 4 out of 5 because the backend logic is tested well across the main scheduling features, but the tests do not fully cover UI behavior, invalid user input, or more advanced real-world scheduling scenarios.

That confidence level is the one I choose. Not 5 out of 5, because even a good backend suite does not prove the whole app is flawless.

## Features
Priority-first task sorting: Tasks are sorted by priority, then by due time, so more important tasks are considered first in the daily plan.

Sorting by time: Tasks can also be sorted chronologically by due time, with tasks that have no due time placed at the end.

Filtering by pet and status: Tasks can be filtered by pet name and by task status, making it easier to view only the relevant tasks.

Time-constrained daily planning: The scheduler greedily fits pending tasks into the owner’s available time budget and skips tasks that do not fit.

Conflict detection and warnings: The scheduler detects overlapping task time windows and returns human-readable warnings instead of failing.

Recurring task creation: When a daily or weekly task is completed, the scheduler can automatically create the next occurrence with the correct next date.

Human-readable plan explanation: explain_plan() generates a formatted summary of the daily plan, including selected tasks and detected conflicts.

Multi-pet support: One owner can manage multiple pets, and the scheduler builds plans across all of them.

Live task status tracking: Each task stores a TaskStatus value such as PENDING, COMPLETE, or SKIPPED, and task status can be updated during use.

Dynamic task updates: Task attributes can be changed at runtime using update_task(**kwargs).

## Demo

**Safe care request — task extraction and scheduling**

![Safe request step 1](assets/app_safe_request/1.png)
![Safe request step 2](assets/app_safe_request/2.png)
![Safe request step 3](assets/app_safe_request/3.png)

**Unsafe request — guardrail block**

![Guardrail warning step 1](assets/app_guardrail_warning/1.png)
![Guardrail warning step 2](assets/app_guardrail_warning/2.png)


## Optional Extensions

**b. Challenge 2: Data Persistence with Agent Mode**

PawPal+ now saves owner, pet, and task data to a data.json file so information is preserved between runs. Agent Mode in VS Code Claude was used to plan the persistence workflow, add JSON save/load behavior to the backend, and connect loading to Streamlit session state on startup. A custom dictionary-based serialization approach was used to keep the solution simple and dependency-light.

Next available slot finder: Given a task duration, the scheduler scans the day from 07:00 to 21:00 in 15-minute increments and returns the first time slot that does not overlap any existing scheduled task. This avoids manually hunting for gaps in a busy schedule.

JSON persistence: Owner, pet, and task data is automatically saved to data.json after every change and reloaded on app startup, so no data is lost between sessions.


**a. Challenge 1: Advanced Algorithmic Capability via Agent Mode**

Next available slot finder: Given a task duration, the scheduler scans the day from 07:00 to 21:00 in 15-minute increments and returns the first time slot that does not overlap any existing scheduled task. This removes the need to manually find gaps in a busy day.

PawPal+ was extended with a next-available-slot feature. This allows the scheduler to suggest an open time window for a new task based on existing tasks and their durations. Agent Mode in VS Code Claude was used to plan the method, integrate it into the Scheduler class, and keep the implementation aligned with the existing object-oriented design.