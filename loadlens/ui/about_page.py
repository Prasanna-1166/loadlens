"""About/Help page for LoadLens."""

from __future__ import annotations

import streamlit as st


def render_about_page() -> None:
    """Render the About & Help page."""
    st.title("ℹ️ About LoadLens")
    st.markdown(
        "**LoadLens** is an explainable workload allocation and capacity planning tool. "
        "Given an ordered sequence of tasks and a number of workers, it finds the optimal "
        "contiguous partition that minimises the maximum workload assigned to any worker."
    )

    st.markdown("---")

    st.subheader("🔧 The Problem")
    st.markdown(
        """
        Given:
        - An ordered list of tasks, each with a positive integer duration.
        - A fixed number of workers.

        Find: The contiguous partition of tasks into exactly *k* non-empty consecutive blocks
        that **minimises the largest block sum** (minimax criterion).

        **Example:**
        - Tasks: J1=7, J2=2, J3=5, J4=10, J5=8 — Total = 32
        - Workers: 3
        - Optimal result: W1=[J1,J2,J3]=14, W2=[J4]=10, W3=[J5]=8 → max = **14**

        The brute-force approach tries all `C(n-1, k-1)` split positions. For n=1000, k=10,
        this is astronomically large. LoadLens solves it in **O(n log R)** time.
        """
    )

    st.subheader("⚡ Algorithm")
    st.markdown(
        """
        **Binary Search on the Answer** — a classic competitive-programming technique:

        1. **Lower bound:** `max(largest_task_duration, ⌈total_duration / workers⌉)`
           — no valid solution can be smaller.
        2. **Upper bound:** `sum(all durations)` — one worker, trivially feasible.
        3. **Feasibility check (O(n)):** Greedily scan tasks; count how many workers are
           needed if each worker's capacity is capped at `C`. Return True if count ≤ k.
        4. **Monotonicity:** Because all durations are positive, increasing C can only merge
           groups. Worker count is monotonically non-increasing in C. Binary search is valid.
        5. **Search (O(log R)):** Binary search on `[low, high]` for the smallest feasible C.
        6. **Reconstruction (O(n)):** Replay the greedy scan with optimal C to produce exactly
           k groups. If greedy produces fewer than k groups, safely subdivide large groups.

        **Total complexity:** O(n log R) time, O(n) space.
        """
    )

    st.subheader("📋 Model Assumptions")
    st.info(
        """
        - Tasks are **indivisible** — each task is assigned to exactly one worker.
        - Task **order is fixed** — no reordering is performed before or after allocation.
        - Assignments are **contiguous** — each worker receives a consecutive slice.
        - All workers have **equal speed** — durations are treated as comparable integers.
        - The model **minimises the maximum workload** (makespan when workers run in parallel).
        - This model does **not** account for: travel time, task precedence networks,
          worker skill levels, variable worker speeds, or non-integer durations.
        """
    )

    st.subheader("📁 CSV Schema")
    st.markdown(
        """
        **Import schema:** `task_name,duration`

        ```csv
        task_name,duration
        Research & Requirements,7
        Database Schema Design,2
        Backend API Development,5
        ```

        **Export columns:** `worker_id, worker_workload, task_order, task_name, task_duration, optimal_capacity`

        - Maximum file size: 5 MB
        - Maximum rows: 10,000 tasks
        - Task names support Unicode characters
        - Durations must be positive integers (no decimals, no negatives, no blanks)
        """
    )

    st.subheader("💾 Local History")
    st.markdown(
        """
        Saved scenarios are stored in a SQLite database in your local app-data directory.

        - No personal data, credentials, or network access required.
        - Database file location: `%LOCALAPPDATA%\\loadlens\\loadlens_scenarios.db` (Windows)
        - **Important:** On hosted platforms (e.g. Streamlit Community Cloud), the filesystem
          is typically ephemeral — saved scenarios may be lost on restart. For durable
          multi-user persistence, configure a hosted database service.
        """
    )

    st.subheader("📦 Technical Stack")
    st.markdown(
        """
        | Component | Technology |
        |-----------|-----------|
        | UI | Streamlit 1.35+ |
        | Algorithm | Pure Python (stdlib only) |
        | Persistence | SQLite (stdlib `sqlite3`) |
        | CSV I/O | stdlib `csv` module |
        | Testing | pytest |
        | Python | 3.12 (tested) |
        """
    )

    st.subheader("🚀 Deployment")
    st.markdown(
        """
        **Streamlit Community Cloud:**
        1. Push the repository to GitHub.
        2. In Community Cloud, set the main file to `streamlit_app.py`.
        3. The `requirements.txt` file lists all dependencies.
        4. See the README for full deployment instructions.

        **Local (Windows PowerShell):**
        ```powershell
        python -m venv .venv
        .venv\\Scripts\\Activate.ps1
        pip install -r requirements.txt
        streamlit run streamlit_app.py
        ```
        """
    )

    st.markdown("---")
    st.caption("LoadLens v1.0.0 — Built with Python & Streamlit. Algorithm: Binary Search on Answer.")
