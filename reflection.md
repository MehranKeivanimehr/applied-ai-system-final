# PawPal+ SafeCare AI — Project Reflection

This document covers the design, implementation, and evaluation of PawPal+ SafeCare AI, the final applied AI system extended from the Module 2 PawPal+ pet-care scheduler.

---

## 1. System Design

**Three core actions the user should be able to perform:**

1. Describe pet-care needs in natural language and have the system extract structured care tasks automatically.
2. Receive safety feedback — a hard block for dangerous requests (toxic foods, emergencies, vet-bypass language) and a soft warning for medication dosage language — before any task is scheduled.
3. Review an observable AI workflow (guardrails → retrieval → parsing → scheduling) and approve parsed tasks before they are added to the daily schedule.

**Initial design — what was planned**

The original Module 2 design had four classes: Owner, Pet, Task, and Scheduler. These handled deterministic scheduling, conflict detection, recurring tasks, and next-available-slot suggestions.

For the final system, three AI-support layers were designed on top of the unchanged scheduler: a safety guardrails module, a local retrieval module, and a natural-language parser. An agentic orchestrator was added to make the workflow observable step-by-step in the Streamlit UI.

**Design changes during implementation**

The most significant change was adding the agentic workflow layer (`agent_workflow.py`) as a wrapper rather than integrating the AI logic directly into `app.py`. This kept the app file thin and made the full pipeline independently testable.

A second change was the retrieval enhancement. The original keyword-overlap retrieval was correct but too narrow. A risk-aware coherence boost was added using seven semantic clusters (toxic substances, medication, emergency, feeding, exercise, grooming, enrichment). If both the query and a knowledge entry share cluster tokens, the entry receives a `+0.4` score bonus, surfacing contextually relevant guidance even when raw keyword overlap is low.

A third change was the task-splitting logic in the parser. The initial version split only on commas and semicolons, missing "and"-joined multi-task sentences like "Brush Luna's coat for 15 minutes and feed her at 7am." A recursive "and" splitter was added that only splits when both sides contain distinct task types, preserving conjunctions within a single task ("walk and run").

---

## 2. AI Pipeline and Tradeoffs

**How the pipeline works**

User input passes through six observable steps:

1. Inspect — validates non-empty input and word count.
2. Guardrails — hard blocks for toxic substances, emergency symptoms, and vet-bypass language; soft warning for specific numeric dosages.
3. Retrieval — keyword + risk-aware scoring over 25 local pet-care entries; species-specific entries are preferred.
4. Parser — regex and keyword extraction converts free text into Task objects with title, type, duration, due time, and priority.
5. Validate — checks task types and durations for sanity.
6. Handoff — passes structured tasks to the existing PawPal+ scheduler.

**One design tradeoff — rule-based parsing over LLM parsing**

The parser uses regex and keyword tables rather than an LLM. This makes the system fully offline (no API key, no network), deterministic (same input always produces the same output), and fast. The tradeoff is that vague or unusual phrasing may produce no tasks. An LLM parser would handle more natural language variation but would require an API key and introduce non-determinism.

**One design tradeoff — local knowledge base over live retrieval**

The knowledge base is a static local JSON file with 25 curated entries. This keeps the system reproducible and avoids the risk of retrieving unsafe or unreliable content from the internet. The tradeoff is coverage: the system cannot answer questions about breeds, conditions, or scenarios not in the knowledge base.

---

## 3. AI Collaboration

**How AI tools were used**

AI was used throughout: planning the module structure, generating initial implementations of the guardrails keyword tables and knowledge base entries, designing the test suite structure, debugging regex patterns, and improving the retrieval scoring logic.

The most useful prompts were narrow and specific — one module or one method at a time. Asking "how should the parser handle dosage patterns that should trigger medication type detection" produced better results than asking "how should I build the parser."

**One moment where AI suggestions were not accepted as-is**

The initial AI suggestion for the "and" splitter used a greedy approach that split on every "and" in the text. This would break phrases like "walk and run for 20 minutes" by treating them as two tasks. The final implementation adds a guard: both sides of the split must contain task keywords from different categories. This required understanding the parser's own keyword tables to write the correct guard condition.

**Verification method**

Every AI-generated code change was verified by running `python -m pytest tests/ -v`. If tests failed, the change was examined and corrected before continuing. The evaluation harness (`evaluate_safecare.py`) was used to verify end-to-end pipeline behavior across 11 representative cases.

---

## 4. Testing and Verification

**What was tested**

The test suite covers the original PawPal+ scheduler (45 tests) and all four new AI modules:

| Module | Tests | What they check |
|---|---|---|
| `guardrails.py` | 20 | Safe inputs, toxic foods per species, emergency symptoms, dosage warnings, vet-bypass blocks |
| `knowledge_base.py` | 17 | Load behavior, empty queries, top-k limits, keyword matching, species filtering |
| `ai_parser.py` | 35 | Empty input, time/duration extraction, task type detection, multi-task parsing, priority ordering |
| `agent_workflow.py` | 29 | Return structure, safe requests, dosage warnings, blocked requests, early-stop behavior, no API key |

**Final test count: 146 / 146 passing.**

**Confidence level: 4 / 5**

The backend logic is tested thoroughly. The main gap is the Streamlit UI, which was validated manually through app screenshots rather than automated browser tests. The parser is also limited by its rule-based design — evaluation cases with clear task keywords pass reliably, but open-ended or ambiguous phrasing may produce no tasks.

**Edge cases tested**

- Empty and whitespace-only inputs blocked before reaching retrieval or parsing.
- Dosage language ("250 mg", "1 tablet") warns but does not block.
- Chocolate, grapes, xylitol, lily, and permethrin blocked per species.
- "Seizing", "not breathing", and "collapse" trigger emergency hard blocks.
- "I don't need a vet" and "instead of a vet" trigger vet-bypass hard blocks.
- Nonsense queries return zero knowledge entries (species bonus gated on keyword score > 0).
- Multi-task "and"-joined sentences produce the correct number of tasks.

---

## 5. Reflection

**What went well**

The layered design was the strongest part of the project. Each module — guardrails, retrieval, parser, scheduler — can be tested, debugged, and explained independently. This made the overall system easier to trust than a single monolithic AI function would have been.

Placing guardrails first in the pipeline was the most important safety decision. Unsafe requests are blocked before retrieval or parsing runs, so no unsafe content ever becomes a scheduled task.

**What could be improved**

The natural-language parser is the weakest component. A rule-based regex parser cannot handle all valid English phrasings of a care request. An LLM-based structured extraction call (with the same return type) could replace the parser loop body without changing the rest of the pipeline — the architecture anticipates this with a comment in `ai_parser.py` marking where the LLM hook would go.

The knowledge base is small and manually curated. Expanding it to cover more species, breeds, ages, and medical conditions would make the retrieval step significantly more useful.

**Key takeaway**

The most important lesson was that safety and reliability in an applied AI system come from constraints, not flexibility. Each guardrail, each validation step, and each deterministic fallback makes the system less surprising and more trustworthy. The system became more reliable not by making the AI layer more powerful, but by making it more bounded.

---

## 6. AI Tool Strategy

AI was most effective when given a single file and a single goal. Multi-file or multi-goal prompts produced longer responses that required more careful review. The best results came from short feedback loops: generate, test, correct, commit.

One AI suggestion that was modified: the early folder structure for the project treated the PawPal+ module as a nested repository. This would have made cloning and evaluation harder. The structure was corrected to a flat root before implementation continued.

One AI suggestion that was accepted and improved the project: keeping the original PawPal+ scheduler completely unchanged and wrapping it with AI modules rather than modifying it. This preserved the fully tested scheduler backend and let the AI layer be added and removed independently.
