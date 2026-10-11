"""Saved Scenarios history page for LoadLens."""

from __future__ import annotations

import json
from typing import Optional

import streamlit as st

from loadlens.models import Task
from loadlens.persistence.scenario_repository import PersistenceError, ScenarioRepository


def render_history_page(repo: Optional[ScenarioRepository]) -> None:
    """Render the Saved Scenarios page."""
    st.title("📂 Saved Scenarios")

    if repo is None:
        st.error(
            "⚠️ Local scenario history is unavailable. "
            "The database could not be initialized (check file system permissions). "
            "The Planner and Algorithm Lab continue to work normally."
        )
        return

    st.markdown(
        "Browse, restore, or delete locally saved allocation scenarios. "
        "History is stored in a local SQLite database on your machine."
    )
    st.caption(
        "ℹ️ **Note:** If you deploy this app to Streamlit Community Cloud or similar "
        "hosted services, the SQLite database lives on an ephemeral filesystem and may "
        "not survive between restarts. For durable storage, use a hosted database service."
    )

    try:
        scenarios = repo.list_all()
    except PersistenceError as e:
        st.error(f"Could not load scenarios: {e}")
        return

    if not scenarios:
        st.info("No saved scenarios yet. Run an optimization in the Planner and click **Save to History**.")
        return

    st.markdown(f"**{len(scenarios)} scenario(s) saved**")

    for scenario in scenarios:
        with st.expander(
            f"#{scenario.scenario_id} — {scenario.name}  •  {scenario.created_at[:19].replace('T', ' ')}",
            expanded=False,
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("Tasks", len(scenario.tasks))
            col2.metric("Workers", scenario.workers)
            col3.metric("Optimal Capacity", scenario.optimal_capacity)

            st.markdown("**Tasks (in order):**")
            task_rows = [
                {"#": i + 1, "Task Name": t.name, "Duration": t.duration}
                for i, t in enumerate(scenario.tasks)
            ]
            st.dataframe(task_rows, use_container_width=True, hide_index=True)

            # Show allocation groups if parseable
            try:
                groups_data = json.loads(scenario.groups_json)
                st.markdown("**Allocation Groups:**")
                for g in groups_data:
                    task_names = " → ".join(t["name"] for t in g["tasks"])
                    st.markdown(
                        f"Worker {g['worker_id']}: {task_names} = **{g['total_duration']}**"
                    )
            except (json.JSONDecodeError, KeyError):
                st.caption("(Allocation detail unavailable)")

            st.caption(f"Algorithm: {scenario.algorithm_version} | Schema v{scenario.schema_version}")

            col_load, col_del = st.columns(2)
            with col_load:
                if st.button("📂 Load into Planner", key=f"load_sc_{scenario.scenario_id}"):
                    # Push tasks into planner session state
                    st.session_state["planner_tasks"] = [
                        {"name": t.name, "duration": t.duration}
                        for t in scenario.tasks
                    ]
                    st.session_state["planner_result"] = None
                    st.session_state["planner_result_stale"] = False
                    st.session_state["planner_workers"] = scenario.workers
                    st.success("Loaded into Planner — navigate to the Planner tab.")

            with col_del:
                # Two-step delete: first click sets a confirm flag
                confirm_key = f"confirm_del_{scenario.scenario_id}"
                if st.session_state.get(confirm_key):
                    if st.button(
                        "⚠️ Confirm Delete", key=f"confirm_del_btn_{scenario.scenario_id}", type="primary"
                    ):
                        try:
                            deleted = repo.delete(scenario.scenario_id)
                            if deleted:
                                st.success("Deleted.")
                            else:
                                st.warning("Not found (already deleted?)")
                        except PersistenceError as e:
                            st.error(f"Delete failed: {e}")
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                else:
                    if st.button("🗑️ Delete", key=f"del_sc_{scenario.scenario_id}"):
                        st.session_state[confirm_key] = True
                        st.rerun()
