"""Workload Allocation Planner page for LoadLens."""

from __future__ import annotations

import json
import math
from typing import List, Optional

import streamlit as st

from loadlens.algorithms.allocation import optimize_allocation
from loadlens.models import AllocationResult, Task
from loadlens.persistence.scenario_repository import PersistenceError, ScenarioRecord, ScenarioRepository
from loadlens.services.csv_service import generate_allocation_csv, parse_csv_tasks
from loadlens.validation import ValidationError

# ── Default example workload ──────────────────────────────────────────────────
_DEFAULT_TASKS = [
    {"name": "Research & Requirements", "duration": 7},
    {"name": "Database Schema Design", "duration": 2},
    {"name": "Backend API Development", "duration": 5},
    {"name": "Frontend Implementation", "duration": 10},
    {"name": "Integration Testing", "duration": 8},
    {"name": "Performance Optimization", "duration": 3},
    {"name": "Documentation", "duration": 4},
    {"name": "Security Audit", "duration": 6},
]

_UNITS = ["units", "minutes", "hours", "days", "story points"]


def _init_session_state() -> None:
    if "planner_tasks" not in st.session_state:
        st.session_state["planner_tasks"] = [
            {"name": t["name"], "duration": t["duration"]} for t in _DEFAULT_TASKS
        ]
    if "planner_result" not in st.session_state:
        st.session_state["planner_result"] = None
    if "planner_result_stale" not in st.session_state:
        st.session_state["planner_result_stale"] = False


def _tasks_from_state() -> List[Task]:
    raw = st.session_state.get("planner_tasks", [])
    return [Task(name=r["name"], duration=int(r["duration"])) for r in raw if r.get("name") and r.get("duration")]


def _render_task_editor() -> None:
    st.subheader("📋 Task List")
    st.caption(
        "Edit task names and durations. Order is preserved — do not re-sort rows manually. "
        "Durations must be positive integers."
    )

    raw_tasks = st.session_state["planner_tasks"]

    # Show a table editor using individual row widgets
    header_cols = st.columns([0.5, 3, 2, 1])
    header_cols[0].markdown("**#**")
    header_cols[1].markdown("**Task Name**")
    header_cols[2].markdown("**Duration**")
    header_cols[3].markdown("**Remove**")

    updated_tasks = []
    rows_to_remove = set()

    for i, task in enumerate(raw_tasks):
        cols = st.columns([0.5, 3, 2, 1])
        cols[0].markdown(f"<div style='padding-top:8px'>{i+1}</div>", unsafe_allow_html=True)
        new_name = cols[1].text_input(
            "Name", value=task["name"], key=f"task_name_{i}", label_visibility="collapsed"
        )
        new_dur = cols[2].text_input(
            "Duration", value=str(task["duration"]), key=f"task_dur_{i}", label_visibility="collapsed"
        )
        if cols[3].button("✕", key=f"task_rm_{i}", help="Remove this task"):
            rows_to_remove.add(i)
            st.session_state["planner_result_stale"] = True

        if i not in rows_to_remove:
            updated_tasks.append({"name": new_name, "duration": new_dur})

    # Persist updates
    if updated_tasks != raw_tasks:
        st.session_state["planner_tasks"] = updated_tasks
        st.session_state["planner_result_stale"] = True

    if rows_to_remove:
        st.session_state["planner_tasks"] = [
            t for i, t in enumerate(raw_tasks) if i not in rows_to_remove
        ]
        st.rerun()

    st.divider()
    col_add, col_reset, col_load = st.columns([1, 1, 2])

    with col_add:
        if st.button("➕ Add Task", use_container_width=True):
            st.session_state["planner_tasks"].append({"name": f"Task {len(raw_tasks)+1}", "duration": "1"})
            st.session_state["planner_result_stale"] = True
            st.rerun()

    with col_reset:
        if st.button("↺ Reset to Example", use_container_width=True):
            st.session_state["planner_tasks"] = [
                {"name": t["name"], "duration": t["duration"]} for t in _DEFAULT_TASKS
            ]
            st.session_state["planner_result"] = None
            st.session_state["planner_result_stale"] = False
            st.rerun()

    with col_load:
        uploaded = st.file_uploader(
            "Upload CSV (task_name, duration)",
            type=["csv"],
            key="csv_uploader",
            help="Schema: task_name,duration — one task per row",
        )
        if uploaded is not None:
            try:
                parsed = parse_csv_tasks(uploaded.read())
                st.session_state["planner_tasks"] = [
                    {"name": t.name, "duration": t.duration} for t in parsed
                ]
                st.session_state["planner_result"] = None
                st.session_state["planner_result_stale"] = False
                st.success(f"✅ Loaded {len(parsed)} tasks from CSV.")
                st.rerun()
            except ValidationError as e:
                st.error(f"CSV Error: {e}")


def _render_config(tasks: List[Task]) -> tuple[int, str]:
    n = len(tasks)
    st.subheader("⚙️ Configuration")
    col_w, col_u = st.columns(2)
    with col_w:
        workers = st.slider(
            "Number of Workers",
            min_value=1,
            max_value=max(n, 1),
            value=min(3, max(n, 1)),
            key="planner_workers",
            help="Each worker receives at least one contiguous block of tasks.",
        )
    with col_u:
        unit = st.selectbox("Duration Unit", _UNITS, key="planner_unit")
    return workers, unit


def _render_results(result: AllocationResult, unit: str, repo: Optional[ScenarioRepository]) -> None:
    st.markdown("---")
    st.subheader("📊 Allocation Results")

    # Stale warning
    if st.session_state.get("planner_result_stale"):
        st.warning("⚠️ The inputs have changed since the last run. Click **Run Optimization** to refresh.")

    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Tasks", result.total_duration and len(result.tasks))
    col2.metric("Total Duration", f"{result.total_duration} {unit}")
    col3.metric("Workers", result.workers)
    col4.metric("Optimal Max Workload", f"{result.optimal_capacity} {unit}")

    col5, col6 = st.columns(2)
    col5.metric(
        "Theoretical Lower Bound",
        f"{result.theoretical_lower_bound} {unit}",
        help="max(largest_task, ⌈total/workers⌉)"
    )
    col6.metric("Feasibility Checks", result.feasibility_checks)

    # Worker allocation table
    st.markdown("#### Worker Assignments")
    rows = []
    for g in result.groups:
        task_names = " → ".join(t.name for t in g.tasks)
        rows.append({
            "Worker": g.worker_id,
            f"Tasks ({len(g.tasks)})": task_names,
            f"Workload ({unit})": g.total_duration,
            f"Headroom ({unit})": g.headroom(result.optimal_capacity),
            "Utilization %": f"{g.utilization_pct(result.optimal_capacity):.1f}%",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Bar chart
    st.markdown("#### Workload vs Optimal Capacity")
    chart_data = {g.worker_id: g.total_duration for g in result.groups}
    opt_line = result.optimal_capacity

    bar_rows = [
        {"Worker": f"W{g.worker_id}", f"Workload ({unit})": g.total_duration}
        for g in result.groups
    ]
    st.bar_chart(
        data={r["Worker"]: r[f"Workload ({unit})"] for r in bar_rows},
        use_container_width=True,
    )
    st.caption(f"🔴 Optimal capacity (maximum allowed workload) = **{opt_line} {unit}**")

    # CSV export
    st.markdown("#### Export")
    csv_str = generate_allocation_csv(result, unit)
    st.download_button(
        label="⬇️ Download Allocation CSV",
        data=csv_str,
        file_name="loadlens_allocation.csv",
        mime="text/csv",
        key="dl_allocation_csv",
    )

    # Save scenario
    if repo is not None:
        st.markdown("#### 💾 Save Scenario")
        scenario_name = st.text_input(
            "Scenario name",
            value=f"Scenario — {len(result.tasks)} tasks, {result.workers} workers",
            key="save_scenario_name",
        )
        if st.button("Save to History", key="btn_save_scenario"):
            groups_json = json.dumps(
                [
                    {
                        "worker_id": g.worker_id,
                        "tasks": [{"name": t.name, "duration": t.duration} for t in g.tasks],
                        "total_duration": g.total_duration,
                    }
                    for g in result.groups
                ]
            )
            rec = ScenarioRecord(
                name=scenario_name.strip() or "Untitled",
                created_at="",
                tasks=result.tasks,
                workers=result.workers,
                optimal_capacity=result.optimal_capacity,
                groups_json=groups_json,
            )
            try:
                saved = repo.save(rec)
                st.success(f"✅ Saved as **{saved.name}** (ID #{saved.scenario_id})")
            except PersistenceError as e:
                st.error(f"Could not save: {e}")
    else:
        st.info("📂 Scenario history is unavailable (database could not be initialized).")


def render_planner_page(repo: Optional[ScenarioRepository]) -> None:
    """Render the full Workload Allocation Planner page."""
    st.title("🔭 LoadLens — Workload Allocation Planner")
    st.markdown(
        """
        **Explainable Workload Allocation & Capacity Planning**

        Given an ordered sequence of tasks and a number of workers, LoadLens finds the optimal
        contiguous partition that *minimises the maximum workload* assigned to any single worker —
        using binary search on the answer paired with a greedy feasibility check.
        """
    )

    with st.expander("ℹ️ Assumptions & Model", expanded=False):
        st.markdown(
            """
            - **Tasks are indivisible** — each task goes to exactly one worker.
            - **Order is fixed** — tasks must be assigned in their original sequence; no re-ordering.
            - **Contiguous blocks** — each worker receives a consecutive slice of the task list.
            - **Equal worker speed** — all workers process tasks at the same rate; durations are integers.
            - **Objective** — minimise the largest worker workload (minimax), not travel time or precedence.
            - Durations must be positive integers; decimal or negative values are rejected.
            """
        )

    _init_session_state()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        _render_task_editor()

    with col_right:
        # Validate tasks before showing config
        try:
            tasks = _tasks_from_state()
            if not tasks:
                st.warning("Add at least one task to continue.")
                return
        except (ValueError, TypeError) as e:
            st.error(f"Task data error: {e}")
            return

        workers, unit = _render_config(tasks)

        run_btn = st.button(
            "▶ Run Optimization",
            type="primary",
            use_container_width=True,
            key="btn_run_optimizer",
        )

        if run_btn:
            try:
                result = optimize_allocation(tasks, workers)
                st.session_state["planner_result"] = result
                st.session_state["planner_result_stale"] = False
                st.success(
                    f"✅ Optimal max workload: **{result.optimal_capacity} {unit}** "
                    f"across {workers} worker(s)."
                )
            except ValidationError as e:
                st.error(f"Validation error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

    result: Optional[AllocationResult] = st.session_state.get("planner_result")
    if result is not None:
        _render_results(result, unit, repo)
