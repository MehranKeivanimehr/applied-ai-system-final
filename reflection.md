# PawPal+ Project Reflection

## 1. System Design

PawPal+ is designed to help a pet owner organize and plan daily pet care activities.

Three core actions the user should be able to perform are:

    1-1. The user should be able to enter and manage basic owner and pet information so the system can support personalized care planning.

    1-2. The user should be able to add, edit, and organize pet care tasks such as feeding, walks, medication, grooming, and enrichment, including important details like duration and priority.

    1-3. The user should be able to generate and review a daily care plan based on task importance, available time, and owner preferences, while also seeing why the plan was selected.


**a. Initial design**

- Briefly describe your initial UML design.
My initial UML design for PawPal+ was kept simple and focused on the main parts of the app. I included four classes: Owner, Pet, Task, and Scheduler. The relationships were straightforward: an Owner can have multiple Pets, each Pet can have multiple Tasks, and the Scheduler works with tasks to build a daily plan.

- What classes did you include, and what responsibilities did you assign to each?
The Owner class was responsible for storing user information such as name, available time, preferences, and the pets they manage. The Pet class represented each pet and held basic details like name, species, age, notes, and its task list. The Task class represented individual care activities such as feeding, walks, medication, or grooming, along with details like duration, priority, due time, recurring status, and completion status. The Scheduler class was responsible for organizing tasks, checking conflicts, and generating a daily schedule based on time and priority.

**b. Design changes**

- Did your design change during implementation?

Yes, the design changed slightly after reviewing the class skeleton.

- If yes, describe at least one change and why you made it.

The main change was in the Scheduler class. In the initial design, Scheduler stored its own available_time and task list. After review, I changed it so that Scheduler works directly with the Owner object instead. This avoids duplicated data and makes it easier for the scheduler to access pets and their tasks when building a daily plan.

I also updated Task.update_task() so it can accept changes more flexibly, and I replaced the raw task status string with a small enum to keep task states more consistent.
---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?

The scheduler considers three constraints:

Available time : generate_daily_plan() tracks time_remaining and skips any task whose duration exceeds what is left. Tasks that don't fit are dropped entirely.
Priority : sort_tasks() sorts by priority descending before building the plan, so higher-priority tasks are considered first and are less likely to get cut by the time limit.
Task status: only PENDING tasks are included. COMPLETE and SKIPPED tasks are filtered out before scheduling.
due_time is used for conflict detection and chronological sorting (sort_by_time()), but does not directly gate whether a task enters the plan.

- How did you decide which constraints mattered most?

Available time was treated as a hard constraint; it cannot be exceeded, so it acts as a strict cutoff. Priority was treated as the primary ordering constraint because a pet care app needs to guarantee that critical tasks (like medication) always get scheduled before optional ones (like enrichment). Status filtering was implicit. there is no reason to re-schedule work that is already done. Due time was kept as a soft constraint because not every task has a fixed start time, and forcing it as a hard gate would drop too many tasks in early use.

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

Reply to both:

One tradeoff in my scheduler is that I chose a lightweight conflict detection approach instead of building a full scheduling engine. The system checks whether task time windows overlap based on stored due time, duration, and date information. This keeps the code simple and readable, which is useful for a small project, but it also means the scheduler is still limited compared with a real calendar-based planning system.

Another tradeoff came up during refinement. AI suggested a more Pythonic version of conflict detection using combinations instead of manual index loops. I kept the simplified version where it improved readability, but I avoided making every method as compact as possible because some shorter solutions are harder for a human reader to follow.
---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?

I used AI mainly for UML brainstorming, class skeleton generation, method design, test planning, debugging, and small refactors. It was most helpful when I asked focused questions about one file or one method at a time.

- What kinds of prompts or questions were most helpful?

The most helpful prompts were specific and technical, such as asking how Scheduler should interact with Owner, how to sort tasks by time, how to handle recurring tasks, and how to improve readability without changing behavior.

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.

One moment where I did not accept an AI suggestion as-is was when it proposed more compact, more Pythonic code for conflict detection. I accepted the simplification that improved readability, but I did not keep every compact version because some were harder to understand.

- How did you evaluate or verify what the AI suggested?

I verified AI suggestions by checking them against my current class design, running main.py, and rerunning python -m pytest. If a suggestion made the code less clear or did not match my actual logic, I changed it before using it.
---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?

I tested task completion, task addition, sorting by time, filtering by pet and status, recurring task creation, conflict detection, and daily plan generation.

- Why were these tests important?

These tests were important because they covered the core scheduling behavior and the main edge cases, such as no tasks, overlapping tasks, completed tasks, and limited available time.

**b. Confidence**

- How confident are you that your scheduler works correctly?

My confidence level is 4/5. The backend logic is tested well, and the main scheduling features behave correctly in both the demo script and pytest suite.

- What edge cases would you test next if you had more time?

If I had more time, I would test more UI-related behavior, invalid user input, duplicate pets or tasks, and more date and time edge cases.

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

The part I am most satisfied with is the separation between the backend logic and the Streamlit UI. The Owner, Pet, Task, and Scheduler design stayed clean while the features became more advanced.

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

If I had another iteration, I would improve the UI more, strengthen validation, and redesign some time handling so dates and times are managed more formally instead of mostly as strings.

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?

One important thing I learned is that AI is most useful when the developer stays in control of the design. Good results came from using AI as a strong assistant, not as the architect of the whole system.


## AI Strategy with VS Code Claude

VS Code Claude was most effective for method-level planning, targeted refactoring, UML updates, and test generation and find the best fix. It worked best when I gave it a narrow scope, such as one class, one method, or one bug not all the files together.

One AI suggestion I rejected or modified was the idea of making several methods more compact just to be more Pythonic. I kept the version that was cleaner to read and easier to maintain.

Using separate chat sessions for different phases helped me stay organized because each phase had a clear goal: design, implementation, UI integration, algorithms, testing, and reflection. That prevented the conversation from becoming mixed and harder to manage.

The biggest lesson about being the lead architect was that I had to make the final design decisions myself. AI could generate options quickly, but I had to decide what matched the project goals, what stayed readable, and what was actually verified by code and tests.


## Optional Extensions

**a. Challenge 1: Advanced Algorithmic Capability via Agent Mode**
**b. Challenge 2: Data Persistence with Agent Mode**
