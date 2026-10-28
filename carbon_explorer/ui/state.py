"""Session state: shared view controls, the scenario builder and saved items.

The builder's editable table follows the anchor pattern: the frame handed to
st.data_editor is stored in session state and only replaced (with a new
widget key) when a helper button, a year change or a scenario load rewrites it.
"""

from __future__ import annotations

from dataclasses import replace

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
NEW_SCENARIO = "__new__"  # scenario picker value for an unsaved scenario

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
    # The saved scenario being changed in the builder (None: a new one).
    ss.sb_editing = None
    ss.sb_pick = NEW_SCENARIO


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


def _names() -> list[str]:
    return [x.name for x in ss.scenarios]


def _editing(name: str | None) -> None:
    """Mark which saved scenario the builder is changing (None: a new one)."""
    ss.sb_editing = name
    ss.sb_pick = name if name is not None else NEW_SCENARIO


def _same_assumptions(a: Scenario, b: Scenario) -> bool:
    return (a.year, dict(a.quantities), a.selected, a.offset_pct, a.project) == (
        b.year, dict(b.quantities), b.selected, b.offset_pct, b.project)


def has_unsaved_changes() -> bool:
    if ss.sb_editing not in _names():
        return True
    saved = ss.scenarios[_names().index(ss.sb_editing)]
    current = current_scenario()
    return current.name != saved.name or not _same_assumptions(current, saved)


def _validated(wb: Workbook) -> Scenario | None:
    try:
        scenario = current_scenario()
        evaluate(wb, scenario)
    except ScenarioError as exc:
        ss._flash = ("error", str(exc))
        return None
    return scenario


def save_as_new(wb: Workbook) -> None:
    scenario = _validated(wb)
    if scenario is None:
        return
    if scenario.name in _names():
        ss._flash = ("error", f"“{scenario.name}” is already used. Type a different name, or "
                              "pick that scenario at the top to change it.")
        return
    ss.scenarios.append(scenario)
    _editing(scenario.name)
    ss._flash = ("success", f"Saved “{scenario.name}”. It is in Compare Scenarios.")


def save_changes(wb: Workbook) -> None:
    old_name = ss.sb_editing
    if old_name not in _names():
        save_as_new(wb)
        return
    scenario = _validated(wb)
    if scenario is None:
        return
    if scenario.name != old_name and scenario.name in _names():
        ss._flash = ("error", f"“{scenario.name}” is already used by another scenario. "
                              "Type a different name.")
        return
    index = _names().index(old_name)
    saved = ss.scenarios[index]
    if _same_assumptions(scenario, saved):
        # Only the name changed: keep the description and example label.
        scenario = replace(saved, name=scenario.name)
    ss.scenarios[index] = scenario
    if scenario.name != old_name:
        for n in ss.notes:
            if n.get("scenario") == old_name:
                n["scenario"] = scenario.name
    _editing(scenario.name)
    ss._flash = ("success", f"Saved changes to “{scenario.name}”.")


def start_new(wb: Workbook) -> None:
    """Begin a new scenario from the workbook forecast for the current year."""
    year = int(ss.sb_year)
    ss.sb_offset = 0
    ss.sb_project = None
    ss.sb_name = next_name()
    _replace_anchor(_anchor(wb, year, wb.quantities_for(year), set(wb.families)))
    _editing(None)


def on_pick(wb: Workbook) -> None:
    if ss.sb_pick == NEW_SCENARIO:
        start_new(wb)
    elif ss.sb_pick in _names():
        load_into_builder(wb, ss.sb_pick, switch_tab=False)


def load_into_builder(wb: Workbook, name: str, switch_tab: bool = True) -> None:
    s = ss.scenarios[_names().index(name)]
    ss.sb_year = s.year
    ss.sb_offset = int(round(s.offset_pct))
    ss.sb_project = s.project
    ss.sb_name = s.name
    _replace_anchor(_anchor(wb, s.year, s.quantities, s.selected))
    _editing(s.name)
    if switch_tab:
        ss.nav = BUILDER_TAB


def delete_scenario(name: str) -> None:
    if name in _names():
        del ss.scenarios[_names().index(name)]
    if ss.sb_editing == name:
        # Keep what is in the builder, now as an unsaved scenario.
        _editing(None)
        ss.sb_name = next_name()
        ss._flash = ("success", f"Deleted “{name}”. The builder still shows its values as "
                                "a new, unsaved scenario.")


def restore_examples(wb: Workbook) -> None:
    names = {s.name for s in ss.scenarios}
    ss.scenarios.extend(s for s in illustrative_scenarios(wb) if s.name not in names)


def clear_scenarios() -> None:
    ss.scenarios = []
    _editing(None)


def pop_flash():
    return ss.pop("_flash", None)
