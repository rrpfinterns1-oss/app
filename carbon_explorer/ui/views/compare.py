"""Tab 4 · Compare Scenarios: saved assumptions and outputs side by side."""

from __future__ import annotations

import json
from dataclasses import replace
from html import escape

import pandas as pd
import streamlit as st

from ...data import Workbook
from ...model import ASSUMPTION, Result, Scenario, ScenarioError, evaluate, interpret, summary
from .. import charts, state
from ..style import card_title, note, prose, section


def _comparison_html(results: list[Result]) -> str:
    head = "".join(
        f"<th>{escape(r.scenario.name)}"
        + ('<span class="ill">Illustrative example</span>' if r.scenario.illustrative else "")
        + "</th>"
        for r in results
    )
    summaries = [summary(r) for r in results]
    body, group = [], None
    for i, (grp, label, _, _) in enumerate(summaries[0]):
        if grp != group:
            group = grp
            title = "Assumptions" if grp == ASSUMPTION else "Factual outputs"
            body.append(f'<tr class="grp"><td>{title}</td>' + "<td></td>" * len(results) + "</tr>")
        cells = []
        for rows in summaries:
            raw, text = rows[i][2], rows[i][3]
            cls = "num" if isinstance(raw, (int, float)) or raw is None else "txt"
            cells.append(f'<td class="{cls}">{escape(text)}</td>')
        body.append(f"<tr><td>{escape(label)}</td>{''.join(cells)}</tr>")
    return (
        '<div class="cx-table-wrap"><table class="cx-table compare">'
        f"<thead><tr><th>Scenario</th>{head}</tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def _export_csv(results: list[Result]) -> bytes:
    summaries = [summary(r) for r in results]
    index = pd.MultiIndex.from_tuples([(g, label) for g, label, _, _ in summaries[0]],
                                      names=["Section", "Measure"])
    data = {r.scenario.name: [row[2] for row in rows] for r, rows in zip(results, summaries)}
    return pd.DataFrame(data, index=index).to_csv().encode("utf-8")


def _import(wb: Workbook, upload) -> None:
    ss = st.session_state
    done = ss.setdefault("_imported_files", set())
    if upload is None or upload.file_id in done:
        return
    done.add(upload.file_id)
    try:
        records = json.loads(upload.getvalue().decode("utf-8"))
        if isinstance(records, dict):
            records = [records]
        imported = [Scenario.from_dict(rec) for rec in records]
        for s in imported:
            evaluate(wb, s)
    except (ValueError, ScenarioError, TypeError) as exc:
        st.error(f"Could not import that file: {exc}")
        return
    names = {s.name for s in ss.scenarios}
    for s in imported:
        name, n = s.name, 2
        while name in names:
            name, n = f"{s.name} ({n})", n + 1
        names.add(name)
        ss.scenarios.append(replace(s, name=name))
    ss._compare_flash = f"Imported {len(imported)} scenario{'s' if len(imported) != 1 else ''}."
    st.rerun()


def render(wb: Workbook) -> None:
    ss = st.session_state
    section(
        "Compare Scenarios",
        "Saved scenarios, side by side",
        "Assumptions and factual outputs for each saved scenario. Examples A–D are "
        "illustrative starting points, one each for a full, partial, targeted and "
        "portfolio-change scenario. They are not recommendations; open, edit or delete them.",
    )

    if not ss.scenarios:
        with st.container(key="card-compare-empty"):
            card_title("No saved scenarios", "Save a scenario in the Scenario Builder, import a "
                       "file, or restore the illustrative examples.")
            st.button("Restore illustrative examples", icon=":material/history:",
                      on_click=state.restore_examples, args=(wb,))
        _manage_files(wb, [])
        return

    flash = ss.pop("_compare_flash", None)
    if flash:
        st.success(flash)
    names = [s.name for s in ss.scenarios]
    shown = st.pills("Scenarios shown", names, selection_mode="multi", default=names)
    picked = [i for i, s in enumerate(ss.scenarios) if s.name in (shown or [])]
    if not picked:
        st.info("Select at least one scenario to compare.")
        _manage_files(wb, [])
        return
    results = [evaluate(wb, ss.scenarios[i]) for i in picked]

    st.html(_comparison_html(results))
    note("Emissions change = scenario − baseline for the scenario's year; negative means "
         "lower modelled emissions. Costs use each scenario's selected project price. "
         "The commercial indicator is a simplified teaching indicator.")

    chart_data = pd.DataFrame({
        "Scenario": [r.scenario.name for r in results],
        "Order": list(range(len(results))),
        "Offset": [r.tonnes_offset for r in results],
        "Not offset": [r.not_offset for r in results],
        "Baseline": [r.baseline_emissions for r in results],
        "Cost": [r.offset_cost for r in results],
    })
    left, right = st.columns([1.35, 1], gap="medium")
    with left, st.container(key="card-compare-coverage"):
        card_title("Scenario emissions and tonnes offset",
                   "Bar = scenario emissions, split into offset and not offset · "
                   "dark tick = baseline for that year")
        charts.show(charts.coverage_by_scenario(chart_data))
    with right, st.container(key="card-compare-cost"):
        card_title("Estimated offset cost", "Tonnes offset × project price per tCO₂e (USD)")
        if chart_data["Cost"].notna().any():
            charts.show(charts.cost_by_scenario(chart_data))
        missing = chart_data.loc[chart_data["Cost"].isna(), "Scenario"].tolist()
        if missing:
            st.caption("No project chosen, so no cost: " + ", ".join(missing) + ".")

    section("Detail", "Each scenario in words")
    for idx, r in zip(picked, results):
        label = r.scenario.name + ("  ·  illustrative" if r.scenario.illustrative else "")
        with st.expander(label):
            if r.scenario.description:
                st.caption(r.scenario.description)
            prose(interpret(r))
            with st.container(horizontal=True, gap="small"):
                st.button("Open in Scenario Builder", key=f"open_{idx}_{r.scenario.name}",
                          icon=":material/edit:", on_click=state.load_into_builder, args=(wb, idx))
                st.button("Delete", key=f"del_{idx}_{r.scenario.name}", icon=":material/delete:",
                          type="tertiary", on_click=state.delete_scenario, args=(idx,))

    _manage_files(wb, results)


def _manage_files(wb: Workbook, results: list[Result]) -> None:
    ss = st.session_state
    section("Files", "Keep or share your scenarios",
            "Saved scenarios last for this browser session. Download them to keep a copy, "
            "and import the file later to carry on.")
    with st.container(key="card-compare-files"):
        with st.container(horizontal=True, gap="small"):
            st.download_button(
                "Comparison table (CSV)", data=_export_csv(results) if results else b"",
                file_name="scenario_comparison.csv", mime="text/csv",
                icon=":material/table_view:", disabled=not results, on_click="ignore",
            )
            st.download_button(
                "Scenarios (JSON)",
                data=json.dumps([s.to_dict() for s in ss.scenarios], indent=2).encode("utf-8"),
                file_name="scenarios.json", mime="application/json",
                icon=":material/download:", disabled=not ss.scenarios, on_click="ignore",
            )
            st.button("Restore illustrative examples", icon=":material/history:",
                      type="tertiary", on_click=state.restore_examples, args=(wb,))
            st.button("Remove all scenarios", icon=":material/delete_sweep:", type="tertiary",
                      on_click=state.clear_scenarios, disabled=not ss.scenarios)
        upload = st.file_uploader("Import scenarios (JSON exported from this app)", type=["json"])
        _import(wb, upload)
