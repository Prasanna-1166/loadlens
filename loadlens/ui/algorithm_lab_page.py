"""Algorithm Lab page for LoadLens.

Two independent educational demonstrations:
1. Binary-search workload allocation trace (uses the core solver).
2. Rotated sorted-array binary search (completely independent).
"""

from __future__ import annotations

import math
from typing import List, Optional

import streamlit as st

from loadlens.algorithms.allocation import optimize_allocation
from loadlens.algorithms.rotated_search import (
    generate_rotated_array,
    rotated_binary_search,
    validate_rotated_array,
)
from loadlens.models import AllocationResult, Task
from loadlens.validation import ValidationError


# ── Built-in example for the trace demo ───────────────────────────────────────
_EXAMPLE_TASKS_LAB = [
    Task("J1", 7), Task("J2", 2), Task("J3", 5), Task("J4", 10), Task("J5", 8),
]


def _render_allocation_trace() -> None:
    """Show the binary-search allocation trace demo."""
    st.subheader("🔍 Allocation Trace — Binary Search on Answer")

    st.markdown(
        """
        This demonstration runs the allocation solver step-by-step and shows every
        binary-search iteration. You can see exactly how the search converges on the
        optimal capacity.

        **How it works:**
        - The algorithm maintains a search range `[low, high]` for the candidate capacity.
        - At each step it tests the midpoint `mid`, counting how many workers are needed
          greedily if the capacity is `mid`.
        - If feasible (`workers_needed ≤ k`), we know the answer is ≤ mid → shrink `high`.
        - If not feasible, we need more room → raise `low`.
        - Because all task durations are positive integers, the feasibility predicate is
          **monotonically non-decreasing**: once a capacity is feasible, all larger values
          remain feasible. This guarantees binary search terminates at the optimum.
        """
    )

    with st.expander("Configure Example"):
        col1, col2 = st.columns(2)
        with col1:
            raw = st.text_area(
                "Task durations (comma-separated integers)",
                value="7, 2, 5, 10, 8",
                key="lab_durations",
                height=68,
            )
        with col2:
            num_workers = st.number_input("Workers", min_value=1, value=3, key="lab_workers")

    if st.button("▶ Run Trace", key="btn_lab_trace"):
        try:
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            tasks = [Task(f"J{i+1}", int(p)) for i, p in enumerate(parts)]
            result: AllocationResult = optimize_allocation(tasks, int(num_workers))
            st.session_state["lab_trace_result"] = result
        except (ValidationError, ValueError) as e:
            st.error(f"Error: {e}")
            st.session_state.pop("lab_trace_result", None)

    result = st.session_state.get("lab_trace_result")
    if result is None:
        # Auto-run example on first load
        try:
            result = optimize_allocation(_EXAMPLE_TASKS_LAB, 3)
            st.session_state["lab_trace_result"] = result
        except Exception:
            pass

    if result is not None:
        st.markdown("---")
        st.markdown("#### Search Parameters")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Lower Bound", result.lower_bound, help="max(max_task, ⌈total/workers⌉)")
        col_b.metric("Upper Bound", result.upper_bound, help="sum of all durations")
        col_c.metric("Optimal Capacity", result.optimal_capacity)

        st.markdown("#### Binary Search Iterations")
        if result.trace:
            trace_rows = []
            for step in result.trace:
                trace_rows.append({
                    "Step": len(trace_rows) + 1,
                    "Low": step.low,
                    "High": step.high,
                    "Mid (candidate)": step.mid,
                    "Workers Needed": step.required_workers,
                    "Feasible?": "✅ Yes" if step.feasible else "❌ No",
                    "New Low": step.new_low,
                    "New High": step.new_high,
                    "Decision": "Shrink high → mid" if step.feasible else "Raise low → mid+1",
                })
            st.dataframe(trace_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Single worker — no binary search needed (optimal = total duration).")

        st.markdown("#### Final Allocation Groups")
        for g in result.groups:
            tasks_str = ", ".join(f"{t.name}({t.duration})" for t in g.tasks)
            st.markdown(
                f"**Worker {g.worker_id}:** {tasks_str}  →  total = **{g.total_duration}** "
                f"(headroom = {g.headroom(result.optimal_capacity)})"
            )

        st.markdown("#### Monotonicity Explanation")
        st.info(
            "**Why binary search works here:** Every task duration is a positive integer, "
            "so increasing the capacity can only merge adjacent groups (it never forces a new split). "
            "The greedy worker count is monotonically non-increasing as capacity grows, "
            "meaning the feasibility predicate transitions from False to True exactly once. "
            "Binary search on this monotonic predicate always finds the exact minimum feasible capacity."
        )


def _render_rotated_search() -> None:
    """Show the rotated sorted-array binary search demo."""
    st.subheader("🔄 Rotated Sorted-Array Binary Search")
    st.markdown(
        """
        **Note:** This is a completely separate educational example.
        The workload allocation optimizer above does *not* use or depend on this algorithm.

        **Problem:** A strictly increasing array has been rotated at an unknown pivot.
        Locate a target value in O(log n) time without first unrotating the array.

        **Key insight:** At every step, one of the two halves is always sorted.
        We can determine which half the target belongs to, then discard the other half.
        """
    )

    st.markdown("#### Input")
    input_mode = st.radio(
        "Array input mode",
        ["Generate from sorted+rotate", "Enter manually"],
        key="rot_input_mode",
        horizontal=True,
    )

    arr: List[int] = []

    if input_mode == "Generate from sorted+rotate":
        col1, col2 = st.columns(2)
        with col1:
            n = st.slider("Array size (n)", 3, 20, 8, key="rot_n")
        with col2:
            offset = st.slider("Rotation offset", 0, n - 1, 3, key="rot_offset")
        arr = generate_rotated_array(n, offset)
        st.write("Generated array:", arr)
    else:
        raw_arr = st.text_input(
            "Array elements (comma-separated integers)",
            value="4, 5, 6, 7, 0, 1, 2",
            key="rot_manual_arr",
        )
        try:
            arr = [int(x.strip()) for x in raw_arr.split(",") if x.strip()]
            validate_rotated_array(arr)
            st.success(f"✅ Valid rotated array: {arr}")
        except ValueError as e:
            st.error(f"Invalid array: {e}")
            arr = []

    target = st.number_input("Target value to search", value=0, key="rot_target")

    if arr and st.button("🔍 Search", key="btn_rot_search"):
        try:
            validate_rotated_array(arr)
            result = rotated_binary_search(arr, int(target))
            st.session_state["rot_result"] = result
        except ValueError as e:
            st.error(f"Validation error: {e}")
            st.session_state.pop("rot_result", None)

    rot_result = st.session_state.get("rot_result")
    if rot_result is not None:
        if rot_result.found:
            st.success(f"✅ Found **{rot_result.target}** at index **{rot_result.index}**")
        else:
            st.warning(f"🔍 **{rot_result.target}** not found in the array.")

        if rot_result.trace:
            st.markdown("#### Search Trace")
            trace_rows = []
            for step in rot_result.trace:
                if step.get("mid", -1) == -1:
                    trace_rows.append({
                        "Step": len(trace_rows) + 1,
                        "Low": step.get("low", ""),
                        "Mid": "—",
                        "High": step.get("high", ""),
                        "arr[mid]": "—",
                        "Decision": step.get("decision", ""),
                        "Half Chosen": step.get("half_chosen", "—"),
                    })
                else:
                    trace_rows.append({
                        "Step": len(trace_rows) + 1,
                        "Low": step["low"],
                        "Mid": step["mid"],
                        "High": step["high"],
                        "arr[mid]": step.get("arr_mid", ""),
                        "Decision": step.get("decision", ""),
                        "Half Chosen": step.get("half_chosen", "—"),
                    })
            st.dataframe(trace_rows, use_container_width=True, hide_index=True)

        st.markdown("#### Edge Cases Explained")
        st.info(
            "**Duplicates are rejected** because they make it impossible to determine "
            "which half is sorted — arr[low] == arr[mid] would be ambiguous. "
            "For duplicate-tolerant rotated search, a different algorithm is required."
        )


def render_algorithm_lab_page() -> None:
    """Render the Algorithm Lab page."""
    st.title("🧪 Algorithm Lab")
    st.markdown(
        "An educational workspace to explore the algorithms that power LoadLens. "
        "Inspect every decision the binary-search solver makes, or try the independent "
        "rotated sorted-array demo."
    )

    tab_alloc, tab_rot = st.tabs([
        "📈 Allocation Trace",
        "🔄 Rotated Array Search",
    ])

    with tab_alloc:
        _render_allocation_trace()

    with tab_rot:
        _render_rotated_search()
