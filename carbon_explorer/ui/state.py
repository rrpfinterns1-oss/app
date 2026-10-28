"""Session state: shared view controls, the scenario builder and saved items.

The builder's editable table follows the anchor pattern: the frame handed to
st.data_editor is stored in session state and only replaced (with a new
widget key) when a helper button, a year change or a scenario load rewrites it.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..data import HORIZON, Workbook
from ..examples import illustrative_scenarios
from ..model import Scenario, ScenarioError, evaluate

TABS = (
    "Portfolio",
    "Emissions",
    "Scenario Builder",
    "Compare Scenarios",
    "Charts",
    "Source Data",
    "Testing",
    "Findings",
)
BUILDER_TAB = TABS[2]

FAMILY, WORKBOOK_QTY, SCENARIO_QTY, OFFSET = "Engine family", "Workbook qty", "Scenario qty", "Offset"

CHART_KINDS = ("Bar", "Line")

# Controls that appear on both the Portfolio and Emissions tabs and stay in step.
SYNCED = (("portfolio_year", "emissions_year"), ("portfolio_chart", "emissions_chart"))

ss = st.session_state


def init(wb: Workbook) -> None:
    if ss.get("_initialised"):
        return
    ss._initialised = True
    ss.nav = TABS[0]
    ss.portfolio_year = HORIZON[0]
    ss.emissions_year = HORIZON[0]
    ss.portfolio_chart = CHART_KINDS[0]
    ss.emissions_chart = CHART_KINDS[0]
    ss.scenarios = illustrative_scenarios(wb)
    ss.notes = []
    ss.sb_year = HORIZON[0]
    ss.sb_offset = 0
    ss.sb_project = None
    ss.sb_ver = 0
    # Start from the workbook forecast with every family selected and 0% offset:
    # no assumption has been applied until the user makes one.
    ss.sb_anchor = _anchor(wb, HORIZON[0], wb.quantities_for(HORIZON[0]), set(wb.families))
    ss.sb_name = next_name()


# ---------------------------------------------------------------------------
# Year and chart-type controls on the Portfolio and Emissions tabs stay in step.


def sync(source: str) -> None:
    for group in SYNCED:
        if source in group:
            for key in group:
                if key != source:
                    ss[key] = ss[source]


# ---------------------------------------------------------------------------
# Scenario builder


def _anchor(wb: Workbook, year: int, quantities: dict[str, int], selected) -> pd.DataFrame:
    forecast = wb.quantities_for(year)
    return pd.DataFrame(
        {
            FAMILY: list(wb.families),
            WORKBOOK_QTY: [forecast[f] for f in wb.families],
            SCENARIO_QTY: [int(quantities[f]) for f in wb.families],
            OFFSET: [f in selected for f in wb.families],
        }
    )


def editor_key() -> str:
    return f"sb_editor_{ss.sb_ver}"


def builder_frame() -> pd.DataFrame:
    """The anchor with the editor's pending edits applied."""
    frame = ss.sb_anchor.copy()
    edits = ss.get(editor_key(), {}).get("edited_rows", {})
    for pos, changes in edits.items():
        for col, value in changes.items():
            if col in frame.columns:
                frame.iat[int(pos), frame.columns.get_loc(col)] = value
    return frame


def _replace_anchor(frame: pd.DataFrame) -> None:
    ss.sb_anchor = frame.reset_index(drop=True)
    ss.sb_ver += 1


def frame_quantities(frame: pd.DataFrame) -> tuple[dict[str, int], list[str]]:
    """Scenario quantities from an editor frame, plus families left blank (read as 0)."""
    quantities, blank = {}, []
    for family, qty in zip(frame[FAMILY], frame[SCENARIO_QTY]):
        if pd.isna(qty):
            blank.append(family)
            qty = 0
        quantities[family] = max(0, int(round(float(qty))))
    return quantities, blank


def frame_selected(frame: pd.DataFrame) -> frozenset[str]:
    return frozenset(f for f, on in zip(frame[FAMILY], frame[OFFSET]) if bool(on))


def on_builder_year(wb: Workbook) -> None:
    frame = builder_frame()
    _replace_anchor(_anchor(wb, ss.sb_year, wb.quantities_for(ss.sb_year), frame_selected(frame)))


def reset_quantities() -> None:
    frame = builder_frame()
    frame[SCENARIO_QTY] = frame[WORKBOOK_QTY]
    _replace_anchor(frame)


def set_selection(mode: str) -> None:
    frame = builder_frame()
    if mode == "all":
        frame[OFFSET] = True
    elif mode == "none":
        frame[OFFSET] = False
    elif mode == "nonzero":
        quantities, _ = frame_quantities(frame)
        frame[OFFSET] = [quantities[f] > 0 for f in frame[FAMILY]]
    _replace_anchor(frame)


def current_scenario(name: str | None = None) -> Scenario:
    frame = builder_frame()
    quantities, _ = frame_quantities(frame)
    return Scenario(
        name=(name if name is not None else ss.get("sb_name", "")).strip(),
        year=int(ss.sb_year),
        quantities=quantities,
        selected=frame_selected(frame),
        offset_pct=float(ss.sb_offset),
        project=ss.sb_project,
    )


def next_name() -> str:
    used = {s.name for s in ss.get("scenarios", [])}
    n = 1
    while f"Scenario {n}" in used:
        n += 1
    return f"Scenario {n}"


def save_current(wb: Workbook) -> None:
    try:
        scenario = current_scenario()
        evaluate(wb, scenario)  # validates
    except ScenarioError as exc:
        ss._flash = ("error", str(exc))
        return
    names = [s.name for s in ss.scenarios]
    if scenario.name in names:
        ss.scenarios[names.index(scenario.name)] = scenario
        ss._flash = ("success", f"Updated “{scenario.name}”. It is in Compare Scenarios.")
    else:
        ss.scenarios.append(scenario)
        ss._flash = ("success", f"Saved “{scenario.name}”. It is in Compare Scenarios.")
    ss.sb_name = next_name()


def load_into_builder(wb: Workbook, index: int) -> None:
    s = ss.scenarios[index]
    ss.sb_year = s.year
    ss.sb_offset = int(round(s.offset_pct))
    ss.sb_project = s.project
    ss.sb_name = s.name
    _replace_anchor(_anchor(wb, s.year, s.quantities, s.selected))
    ss.nav = BUILDER_TAB


def delete_scenario(index: int) -> None:
    del ss.scenarios[index]


def restore_examples(wb: Workbook) -> None:
    names = {s.name for s in ss.scenarios}
    ss.scenarios.extend(s for s in illustrative_scenarios(wb) if s.name not in names)


def clear_scenarios() -> None:
    ss.scenarios = []


def pop_flash():
    return ss.pop("_flash", None)
