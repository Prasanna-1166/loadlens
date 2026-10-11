# LoadLens — Standalone Master Prompt for an AI Coding Agent

> **Use:** Paste this entire prompt into Claude Code, Google Antigravity, Cursor, or another repository-aware coding agent. The agent must implement the project in the working repository, run the tests it can run, fix defects, and report honestly what was verified.

---

## ROLE

Act as a senior Python engineer, software architect, product-minded developer, algorithm reviewer, UI/UX engineer, and QA engineer. You are responsible for delivering a finished, runnable, maintainable project—not just a plan, tutorial, mockup, or code snippets.

Work autonomously within the repository. Make sensible low-risk decisions without asking questions that can be resolved from this specification. Do not stop after writing an implementation plan. Inspect, implement, test, fix, document, and verify the application end to end.

## 1. PROJECT DECISION AND OBJECTIVE

**Project name:** LoadLens  
**Tagline:** Explainable Workload Allocation & Capacity Planning  
**Category:** Python, Data Structures and Algorithms, optimization, interactive analytics dashboard.

Build a polished application that answers this practical question:

> Given an ordered sequence of jobs, each with a positive integer processing duration, and a chosen number of workers, what is the smallest possible maximum workload assigned to any worker when every worker receives at least one contiguous block of jobs and the original job order is preserved?

Example input:

- Jobs and durations: `J1=7, J2=2, J3=5, J4=10, J5=8`
- Workers: `3`
- The app must calculate a valid contiguous partition that minimizes the largest worker workload, show the optimal maximum workload, explain the decision process, and report each worker's assigned jobs and total duration.

The app is an **allocation planner and algorithm-exploration tool**, not a shortest-path route finder and not a machine-learning product. Do not add AI APIs, authentication, payments, microservices, external databases, or features that require credentials. It must run locally on Windows with Python and be deployable as a simple Streamlit app if the owner chooses.

### Why this project exists

The key engineering value is the transparent combination of:

1. Binary search on the answer (candidate maximum workload).
2. A greedy feasibility checker that calculates the minimum number of workers needed under a capacity limit.
3. Reconstruction of exactly the requested number of non-empty contiguous groups.
4. Independent correctness checks against an exhaustive brute-force solver on small inputs.
5. A real UI, import/export, saved scenarios, docs, and a complete test suite.

Do not claim the algorithm is novel. The value is a correct, well-engineered, explainable implementation packaged as a useful application.

## 2. REPOSITORY-FIRST RULES

Before changing anything:

1. Inspect the current working directory, Git status, existing files, Python version, dependency files, and available test/lint commands.
2. If the repository already contains an application, understand it and preserve working functionality. Do not replace the project wholesale merely to match the suggested tree below.
3. If the directory is empty, create the project structure in Section 9.
4. Never modify files outside the repository root. Never delete unrelated files. Do not overwrite existing user work without a clear reason.
5. If existing code provides a good solution for a requirement, reuse it rather than duplicating it.
6. Establish an implementation plan internally, then start coding immediately. Only ask a question if a missing decision blocks safe, correct implementation.
7. Do not report a command, test, build, screenshot, deployment, or behavior as verified unless it was actually run or observed. Clearly distinguish verified results from unverified limitations.

## 3. REQUIRED FUNCTIONAL SCOPE

### A. Workload Allocation Planner — primary feature

Provide a professional, interactive page where a user can:

- Start from a built-in example workload.
- Edit the ordered task table. Each task has a readable name and a positive integer duration.
- Upload a CSV file using the documented schema `task_name,duration`.
- Select the number of workers. The valid range is `1 <= workers <= number_of_tasks`.
- Select a display unit such as minutes, seconds, or generic units. The unit changes labels only; the algorithm always calculates with integers.
- Run the optimization and inspect the result.
- Download the allocation and its task assignments as a CSV file.
- Save a named result as a local scenario when persistence is available.

**Input rules:**

- Task order is meaningful and must be preserved exactly. Never sort jobs by name, duration, or any other column before allocation.
- Each duration must be a positive integer. Reject zero, negative, non-finite, decimal, blank, or malformed durations with a useful message.
- Reject an empty task list, invalid worker count, duplicate/ambiguous required CSV headers, malformed CSV rows, and files above a documented safe size/row limit.
- Use a documented reasonable safety limit (for example, 10,000 tasks and a 5 MB CSV upload limit) to keep the interface responsive. Validate again in the core/service layer; UI checks alone are insufficient.
- Support Unicode task names. Give clear row-level validation messages where practical.
- Do not silently drop malformed rows or quietly alter the input order.

### B. Optimization algorithm — implement in pure Python

Implement the core independently from Streamlit. Keep it deterministic and easy to test.

For durations `d[0..n-1]` and `k` workers:

- A valid allocation consists of exactly `k` non-empty, contiguous groups in original order.
- The objective is to minimize the largest sum among all groups.
- Use a valid initial lower bound, at least `max(durations)` and optionally the stronger `max(max(durations), ceil(sum(durations) / k))`.
- Use `sum(durations)` as a valid upper bound.
- Binary-search the integer capacity range.
- For a candidate capacity `C`, greedily scan jobs from left to right, starting a new group whenever adding the next job would exceed `C`. Return the minimum number of groups required.
- The candidate is feasible if the greedy checker needs no more than `k` groups. Explain why, because durations are positive and order is fixed, increasing `C` cannot make a previously feasible allocation infeasible; this is the monotonic predicate that makes binary search valid.
- After finding the minimum feasible capacity, reconstruct exactly `k` non-empty contiguous groups. Ensure every group total is at most the optimum. Do not return fewer groups merely because the greedy feasibility pass uses fewer than `k` groups; split blocks safely when needed, preserving order and capacity.
- Return structured result data, not formatted UI strings.
- Record a trace for each binary-search iteration: current lower bound, upper bound, midpoint/candidate capacity, required worker count, feasibility result, and updated interval (or equivalent unambiguous fields).
- Include clear docstrings explaining the invariants and edge cases.

Expected complexity for the main solver: `O(n log R)` time, where `n` is the number of tasks and `R` is the integer search-range width (bounded by the sum of durations); the feasibility scan is `O(n)` per iteration. Document the precise bounds and avoid misleading comparisons.

Suggested clean core API (adapt names if the existing project has a better design):

- `validate_tasks(tasks)`
- `required_workers(durations, capacity)`
- `is_capacity_feasible(durations, workers, capacity)`
- `optimize_allocation(tasks, workers)` returning an `AllocationResult`
- `reconstruct_groups(tasks, workers, optimal_capacity)`

Use type hints, dataclasses or similarly clear typed structures, explicit exceptions, and no global mutable algorithm state. Do not use brute force as the production solver.

### C. Algorithm Lab

Include a dedicated educational page or section that makes the logic understandable to a student and interviewer.

**Allocation trace:**

- Show each binary-search iteration in a readable table.
- Identify the candidate capacity and the greedy number of workers required.
- Explain whether the candidate passed and why the bounds move.
- Provide a visual representation of the final contiguous groups, worker totals, and the optimal capacity.
- Explain the search bounds and monotonic feasibility condition in plain English.
- Avoid claiming that a single arbitrary partition is automatically optimal; connect the result to the smallest feasible candidate capacity.

**Rotated sorted-array search:**

The source project list also mentions rotated-array binary search. Implement a small, clearly separated secondary demonstration under the same Algorithm Lab, not as a dependency of the workload solver.

- Accept a user-provided array of distinct integers or generate a sorted array and rotate it by a selected offset.
- Accept a target integer.
- Use binary search to locate the target in a rotated strictly increasing array, returning its zero-based index or “not found.”
- Display each `low`, `mid`, and `high` iteration and the half selected for the next step.
- Validate that a manually entered array is a valid rotation of a strictly increasing array with distinct values. Reject duplicates and invalid order with an explanatory message instead of producing a potentially incorrect result.
- Cover empty/single-element arrays, unrotated input, rotation at the boundary, negative integers, first/last element targets, and missing targets in tests.
- Explain this is a separate teaching example; the allocation optimizer itself does not depend on rotated-array search.

### D. Workload analytics

After a successful allocation, display:

- Total number of jobs.
- Total processing duration.
- Number of workers.
- Optimal maximum workload (primary result).
- Theoretical lower bound `max(max_job_duration, ceil(total_duration / workers))` for explanation.
- Number of binary-search feasibility checks.
- A worker-by-worker table with ordered task names, start/end positions, workload, capacity headroom, and percentage of the optimal capacity used (handle zero division safely; durations themselves are positive).
- A clear bar chart comparing each worker's total duration with the optimal capacity.

Do not invent data, benchmarks, business impact, or speedup claims. Labels must make units clear. Charts must be based on the actual computed result and must remain understandable on narrow screens.

### E. CSV import/export

- Include a sample CSV under `samples/` and document its exact header/schema.
- Parse uploaded data safely, enforce size/row limits, validate required columns and every row, and show readable errors.
- Export a task assignment report with worker ID, worker workload, task order, task name, task duration, and optimum capacity.
- Use Python's standard `csv` module where practical; do not introduce a large dependency just to read/write CSV.
- Treat uploaded values as untrusted data. Never evaluate or execute values from a CSV. Escape spreadsheet-formula-leading task names in generated CSV exports (for example leading `=`, `+`, `-`, or `@`) or document and implement an equivalent safe export strategy.
- If supporting scenario JSON exports, use ordinary JSON serialization only; never load pickle or execute serialized data.

### F. Local scenario history

Use SQLite from Python's standard library for local history; no hosted database account is needed.

- Save a scenario name, creation timestamp, ordered input tasks, worker count, resulting optimum, grouped allocation, and algorithm version/schema version.
- Support viewing history, opening a saved scenario, and deleting an individual saved scenario after confirmation.
- Use parameterized SQL, explicit transactions, and a small repository/data-access layer separate from UI code.
- Create tables safely on startup using `CREATE TABLE IF NOT EXISTS` or a similarly safe initialization path.
- Put the database in a predictable local data directory and add generated database files to `.gitignore`.
- If the database cannot be created or written, show a clear warning and keep the core planner working. Persistence failure must not crash optimization.
- Document that SQLite history is local-first. A hosted app's writable filesystem may not provide durable storage across restarts; do not promise cloud persistence without a durable database service.
- No login, personal information, secrets, or payment data are needed.

### G. Small, safe benchmark demonstration (secondary priority)

If it fits cleanly after the core and tests are complete, add a demonstration that compares the production binary-search solver with a naive capacity-by-capacity scan on the same small input.

- Guard it using a strict maximum number of capacities checked, so untrusted inputs cannot trigger an enormous slow scan.
- Measure actual local runtime with `time.perf_counter()`; use repeat runs if useful.
- Show the number of feasibility checks alongside runtime.
- Label timings as machine-dependent educational measurements, not universal performance claims.
- Disable or explain the comparison whenever the linear scan would exceed the safe threshold.
- Never make timing assertions part of unit tests.

Do not let this optional feature delay the correctness, usability, or documentation of the primary project.

## 4. USER INTERFACE AND UX QUALITY

The UI must look like a deliberate, professional developer tool—not a default tutorial app or generic AI-generated dashboard.

- Use Streamlit and its supported native components first. Use `st.Page`/`st.navigation` for multipage navigation if it fits the installed compatible version; otherwise choose a clean, supported navigation arrangement and document the choice.
- Use a consistent design system: clear typography hierarchy, spacing, restrained colors, well-aligned metric cards, readable tables, concise labels, and useful empty/error/success states.
- Use native charts and widgets where sufficient. Do not add Plotly or other heavy libraries without a concrete need.
- Design the main planner for a wide screen while remaining usable on smaller screens.
- Main navigation should be obvious: **Planner**, **Algorithm Lab**, **Saved Scenarios**, and **About** (or equivalent logical names).
- Provide a first-run sample scenario so the app looks complete and useful immediately.
- Show a clear loading/progress state only for genuinely expensive work. Do not add fake loading spinners or artificial delays.
- Preserve widget state where expected. Use stable, unique widget keys. Prevent stale results from being presented as if they belong to newly edited inputs; make it obvious when a result needs recalculation.
- Avoid emoji-heavy UI, excessive animations, decorative elements that reduce readability, placeholder buttons, and dead controls.
- Custom CSS may be used sparingly for consistency. Do not rely on fragile selectors or hide essential controls.
- All displayed metrics, tables, traces, and charts must derive from real application state and calculation results.
- Add clear Help/Assumptions text explaining that jobs are indivisible, job order is fixed, worker speeds are treated as equal, durations are positive integers, and the model minimizes the maximum assigned workload rather than modeling travel time, precedence networks, worker skills, or arbitrary scheduling constraints.

## 5. ARCHITECTURE AND ENGINEERING STANDARDS

Keep the algorithm pure and framework-independent. UI, validation, CSV handling, persistence, and domain logic should not be tangled into one large Streamlit file.

Required standards:

- Supported modern Python version compatible with the selected Streamlit release and target deployment; document the tested version. Do not invent unsupported package versions or APIs—verify them from current official documentation or the installed environment.
- Type hints on public functions and core data models.
- Small, cohesive modules with clear names and meaningful docstrings.
- Clear separation between domain models, allocation algorithms, input/CSV validation, SQLite repository, and UI rendering.
- No unnecessary design patterns, microservices, dependency injection framework, ORM, or web backend.
- No credentials or network requests required by the core application.
- No hidden network dependency in the algorithm or sample data.
- Friendly user-facing errors; detailed stack traces belong in developer logs, not normal UI.
- Use the standard library for SQLite, CSV, timestamps, paths, JSON, and performance timing wherever suitable.
- Avoid unnecessary dependency sprawl. Pin or bound the direct dependency versions after verifying compatibility, and use a single deployment dependency file so hosting setup is predictable.
- Include `.gitignore` rules for virtual environments, caches, test output, secrets, and the local SQLite database.
- Never commit `.env` files, credentials, personal datasets, runtime databases, or machine-specific paths.

## 6. TESTING REQUIREMENTS — MANDATORY

Use `pytest` and test the pure core directly without starting a browser for every algorithm test.

### Allocation solver tests

Cover at least:

1. One task and one worker.
2. One worker: optimum equals total duration.
3. One worker per task: optimum equals the largest task duration.
4. Equal durations.
5. Highly uneven durations.
6. A workload where optimal partitions are not equal in task count.
7. `workers=1` and `workers=n` boundaries.
8. Empty task list.
9. Zero/negative duration, decimal duration, malformed duration, and invalid worker counts.
10. Reconstructed allocation has exactly `k` groups, all groups are non-empty, input order is preserved, every task appears exactly once, and each group sum is at most the optimum.
11. The capacity checker returns monotonic feasibility as the candidate capacity increases.
12. Trace bounds progress and termination for valid inputs.
13. CSV headers, malformed rows, blank cells, negative/decimal values, file/row limits, and safe export behavior.
14. Scenario persistence CRUD and graceful handling of persistence errors.

### Independent correctness verification

Implement a simple exhaustive/brute-force reference solver **for tests only** on small input arrays by enumerating all placements of `k-1` split points among the `n-1` gaps. Compare the production solver's optimum against this reference for many deterministic small cases (include a seeded random test). Do not call the production binary-search solver from the reference implementation; the verification must be independent.

### Rotated-array search tests

Cover valid rotations, empty input, singleton, no rotation, first/last targets, absent targets, negative values, invalid ordering, and duplicates.

### App smoke test

Where practical, use Streamlit's supported testing utilities (such as its app testing API) to smoke-test app startup and at least a primary page. If the runtime does not support a particular UI test, document the limitation and run the strongest available import/compile/startup check. Do not pretend an unrun UI test passed.

### Quality checks

Run the checks that are available and relevant, such as:

- `python -m pytest -q`
- `python -m compileall loadlens streamlit_app.py`
- import/smoke check of the entrypoint and core modules
- a manual Streamlit launch if the environment permits

Fix failures rather than merely reporting them. Do not write brittle tests that assert a specific runtime speed.

Add a simple GitHub Actions workflow that installs the declared requirements and runs the automated tests if it fits the repo cleanly. Do not block local operation on CI configuration.

## 7. DOCUMENTATION AND PORTFOLIO READINESS

Create a complete `README.md` with:

1. Project title and clear one-sentence purpose.
2. The real-world problem and explicit model assumptions.
3. Feature list and a concise architecture overview.
4. How the binary-search-on-answer algorithm works.
5. Why the feasibility predicate is monotonic.
6. A worked example showing candidate-capacity decisions and final allocation.
7. Time and space complexity.
8. A Mermaid architecture/data-flow diagram if supported by the repository's documentation conventions.
9. Python/environment prerequisites and exact Windows PowerShell setup/run/test commands.
10. CSV input schema with an example.
11. SQLite local-history behavior and hosted-filesystem caveat.
12. Deployment steps for Streamlit Community Cloud, including the actual entrypoint file and dependency-file location, but no claim that deployment has occurred unless it was done.
13. Limitations and possible next steps, kept realistic.
14. A section for genuine screenshots only if screenshots were actually generated and checked; do not include broken image paths or fabricated badges.

Add `docs/ALGORITHM_WALKTHROUGH.md` with pseudocode, an illustrative trace, correctness intuition, and edge-case behavior. Make documentation understandable enough that the owner can explain the project in an interview.

Create a small, realistic `samples/tasks_example.csv`. The sample data must be clearly labeled as synthetic. Do not create user/customer personal data.

## 8. SECURITY, PRIVACY, AND RELIABILITY

- Core execution must work without API keys, secrets, or network access after dependencies are installed.
- Validate data on the backend/domain boundary, not only through UI widgets.
- Limit uploaded file bytes and rows.
- Do not evaluate user-provided strings or construct SQL by concatenating user values.
- Use SQLite parameterized queries and explicit transaction behavior.
- Do not log full uploaded datasets or store more information than necessary.
- Handle invalid input, missing files, local database permission failures, and malformed scenario records without crashing the complete app.
- Keep filesystem paths platform-independent with `pathlib`; test on Windows-friendly path assumptions and avoid hard-coded drive letters.
- Avoid unnecessary third-party system dependencies. The project must be practical for a student with VS Code and Python on Windows.

## 9. SUGGESTED FILE STRUCTURE

Adapt this structure to fit the inspected repository; do not force unnecessary files into an existing good design.

```text
LoadLens/
├── streamlit_app.py
├── loadlens/
│   ├── __init__.py
│   ├── models.py
│   ├── validation.py
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── allocation.py
│   │   └── rotated_search.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── csv_service.py
│   ├── persistence/
│   │   ├── __init__.py
│   │   └── scenario_repository.py
│   └── ui/
│       ├── __init__.py
│       ├── planner_page.py
│       ├── algorithm_lab_page.py
│       ├── history_page.py
│       └── about_page.py
├── tests/
│   ├── test_allocation.py
│   ├── test_allocation_reference.py
│   ├── test_rotated_search.py
│   ├── test_csv_service.py
│   └── test_scenario_repository.py
├── samples/
│   └── tasks_example.csv
├── docs/
│   └── ALGORITHM_WALKTHROUGH.md
├── .github/
│   └── workflows/
│       └── tests.yml
├── .streamlit/
│   └── config.toml
├── requirements.txt
├── .gitignore
└── README.md
```

Keep module names consistent with actual imports. If pages are implemented as functions, route them through the installed Streamlit version's supported navigation API. Do not create empty placeholder modules that are never used.

## 10. IMPLEMENTATION ORDER

Proceed in this order to minimize rework:

### Phase 1 — Core algorithm and correctness

- Create domain models and input validation.
- Implement the capacity feasibility checker, binary search, trace recording, and exact-group reconstruction.
- Implement rotated-array search.
- Write and run core tests, including independent exhaustive cross-checks.
- Do not build the main UI on top of untested algorithm code.

### Phase 2 — Data handling and persistence

- Add CSV import/export and sample data.
- Add the SQLite scenario repository and its tests.
- Ensure the core algorithm remains independent of Streamlit and SQLite.

### Phase 3 — Working UI

- Build the planner, trace display, worker utilization chart, rotated-array demo, scenario history, and about/help section.
- Use realistic sample values, polished native controls, responsive layout, and consistent labeling.
- Wire every action to real behavior. No dead buttons, fake data, placeholder charts, TODO handlers, or “coming soon” core features.

### Phase 4 — Documentation and operational quality

- Add setup instructions, algorithm walkthrough, `.gitignore`, dependency file, and CI workflow.
- Run all checks, fix discovered defects, and smoke-test the app as far as the environment permits.
- Verify links and paths in the README. Do not create fake screenshots or deployment URLs.

## 11. ACCEPTANCE CRITERIA — DO NOT MARK COMPLETE UNTIL CHECKED

- [ ] The application launches using documented commands in a fresh virtual environment.
- [ ] A user can edit tasks, set a valid worker count, run the optimization, and get a correct allocation.
- [ ] The result is the minimum feasible maximum workload, validated against an independent brute-force reference for small cases.
- [ ] Exactly the chosen number of non-empty contiguous groups is returned; task order is unchanged and no task is lost or duplicated.
- [ ] The binary-search trace matches the actual solver decisions.
- [ ] CSV upload and export work, malformed input is rejected clearly, and sample CSV is included.
- [ ] Workload charts and metrics reflect actual outputs and label units correctly.
- [ ] Rotated-array search works and rejects unsupported inputs clearly.
- [ ] Local scenario saving/loading/deleting works; if persistence cannot start, the rest of the app still works.
- [ ] Automated tests pass, or every remaining failure and its exact cause is reported honestly.
- [ ] No secrets, credentials, machine-specific paths, or local database files are committed.
- [ ] README contains copy-pasteable Windows PowerShell commands and an interview-friendly algorithm explanation.
- [ ] No unimplemented placeholders or misleading success states remain in the required scope.

## 12. FINAL RESPONSE FORMAT

After implementation, provide a precise completion report with these headings:

1. **PROJECT STATUS** — what is implemented and what is not.
2. **ARCHITECTURE** — concise explanation of core modules and data flow.
3. **CREATE / MODIFY / DELETE / DO NOT TOUCH** — exact files changed. Include `DELETE: None` unless deletion was necessary and explicitly justified.
4. **HOW TO RUN ON WINDOWS** — tested commands for virtual environment creation, dependency installation, app launch, and tests.
5. **TESTS AND VERIFICATION** — commands actually executed, pass/fail counts, and any checks not run.
6. **KEY ALGORITHM** — explain the lower/upper bounds, feasibility check, monotonicity, and complexity in simple but correct terms.
7. **LIMITATIONS** — real constraints, including any deployment/persistence caveat.
8. **NEXT STEPS** — only essential owner actions, such as pushing the repository or deploying it; do not imply those actions were already completed.

Be direct and evidence-based. Do not claim a public deployment, CI run, test pass, screenshot, performance result, or security property that you did not verify.

## 13. IMPLEMENT NOW

Inspect the working repository, then carry out Phases 1–4. Deliver the complete usable project, not a proposal for how someone else could build it. Prefer the smallest clear implementation that satisfies the acceptance criteria and explain any justified deviation from this specification in the final report.

---

## Research and design references

Use these as technical references; verify current API details and compatibility before relying on a version-specific feature.

- Binary search and searching a monotonic predicate: https://cp-algorithms.com/num_methods/binary_search.html
- Streamlit multipage app navigation: https://docs.streamlit.io/develop/concepts/multipage-apps/overview
- Streamlit file uploads and widget behavior: https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader
- Streamlit Community Cloud dependency configuration: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- Python SQLite interface: https://docs.python.org/3/library/sqlite3.html
- Python CSV interface: https://docs.python.org/3/library/csv.html
- GitHub repository README best practices: https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories
