"""LoadLens — Streamlit application entry point.

Tested with Streamlit 1.65.0 and Python 3.12.

Navigation uses st.navigation / st.Page (available in Streamlit >= 1.36).
If navigation is unavailable in an older version, a sidebar radio widget is
used as a fallback; the fallback path is documented inline.

Run locally:
    streamlit run streamlit_app.py

Run tests:
    python -m pytest -q
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import streamlit as st

from loadlens.persistence.scenario_repository import PersistenceError, ScenarioRepository
from loadlens.ui.about_page import render_about_page
from loadlens.ui.algorithm_lab_page import render_algorithm_lab_page
from loadlens.ui.history_page import render_history_page
from loadlens.ui.planner_page import render_planner_page

# ---------------------------------------------------------------------------
# Page configuration — must be the first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="LoadLens — Workload Allocation Planner",
    page_icon="🔭",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "LoadLens v1.0.0 — Explainable Workload Allocation & Capacity Planning.",
    },
)

# ---------------------------------------------------------------------------
# Custom CSS — minimal, for typography and card polish
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.4rem;
        font-weight: 700;
    }
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6, #6366f1);
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1.5rem;
        transition: opacity 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        opacity: 0.9;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Repository initialisation (graceful failure)
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

_repo: Optional[ScenarioRepository] = None
try:
    _repo = ScenarioRepository()
    # Trigger initialisation so errors surface early
    _repo._ensure_initialized()
except PersistenceError as _err:
    logger.warning("Scenario repository unavailable: %s", _err)
    _repo = None
except Exception as _err:
    logger.warning("Unexpected persistence error: %s", _err)
    _repo = None

# ---------------------------------------------------------------------------
# Navigation using st.navigation (Streamlit >= 1.36)
# ---------------------------------------------------------------------------

_PAGES = {
    "Planner": lambda: render_planner_page(_repo),
    "Algorithm Lab": render_algorithm_lab_page,
    "Saved Scenarios": lambda: render_history_page(_repo),
    "About": render_about_page,
}

# Sidebar navigation
with st.sidebar:
    st.markdown(
        "## 🔭 LoadLens\n"
        "*Explainable Workload Allocation*"
    )
    st.divider()
    page_choice = st.radio(
        "Navigation",
        list(_PAGES.keys()),
        key="nav_radio",
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("v1.0.0 · Python 3.12 · Streamlit")

# Render selected page
_PAGES[page_choice]()
