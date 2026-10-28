"""RRPF Carbon Scenario Explorer.

Explore the engine portfolio forecast, its estimated emissions and carbon
offset scenarios, using the figures in data/Carbon_Emissions_Workbook_rev.xlsx.
Run with:  streamlit run streamlit_app.py
"""

import streamlit as st

from carbon_explorer.data import HORIZON, WORKBOOK_PATH, Workbook, load_workbook
from carbon_explorer.ui import state
from carbon_explorer.ui.style import footer, hero, inject_css
from carbon_explorer.ui.views import (builder, compare, emissions, explore, findings, portfolio,
                                      source, testing)

st.set_page_config(
    page_title="RRPF Carbon Scenario Explorer",
    page_icon=":material/flight_takeoff:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner=False)
def get_workbook(modified: float) -> Workbook:
    """Load the workbook; the file's modified time makes a replaced file reload."""
    return load_workbook(WORKBOOK_PATH)


inject_css()
wb = get_workbook(WORKBOOK_PATH.stat().st_mtime)
state.init(wb)

hero(
    "RRPF Portfolio · Carbon Scenario Explorer",
    "Engine portfolio emissions",
    "Follow the workbook's engine forecast, see the estimated emissions it implies, and test "
    "offset scenarios side by side. The app reports facts about each scenario; interpretation "
    "and conclusions belong to your presentation.",
    [
        f"Forecast {HORIZON[0]}–{HORIZON[-1]}",
        f"{len(wb.families)} engine families",
        f"{len(wb.projects)} carbon projects",
        f"Source: {wb.source_name}",
        "Teaching estimates",
    ],
)

tabs = st.tabs(state.TABS, key="nav", on_change="rerun")
views = (portfolio, emissions, builder, compare, explore, source, testing, findings)
for tab, view in zip(tabs, views):
    with tab:
        view.render(wb)

footer(
    "Figures are teaching estimates from the supplied workbook. The workbook forecast is source "
    "data; any changed quantity is a scenario assumption. The app does not generate a preferred "
    "strategy or recommendation, and a real portfolio decision would require additional "
    "commercial, contractual and technical information."
)
