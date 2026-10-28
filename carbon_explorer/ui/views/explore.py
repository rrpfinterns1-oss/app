"""Charts tab: show any of the app's data as a bar or line chart.

With "Use my own numbers" switched on, the inputs behind the chosen data can be
typed over and the chart redraws from them. Those numbers are user assumptions:
they stay in this tab and never change the workbook or the Scenario Builder.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
import streamlit as st

from ...data import HORIZON, Workbook
from ...fmt import num
from ...model import evaluate
from ...whatif import Inputs, changes, with_overrides, workbook_inputs
from .. import charts
from ..state import BUILDER_TAB, CHART_KINDS
from ..style import SERIES, card_title, fit_rows, note, section, tag

TOTAL = "Portfolio total"
MAX_SERIES = len(SERIES)


@dataclass(frozen=True)
class Dataset:
    label: str
    unit: str            # shown in titles and tooltips
    over_time: bool      # True: one value per family per year
    build: Callable[[Workbook, Inputs], pd.DataFrame]
    label_format: str = ",.0f"
    keep_order: bool = False
    note: str = ""


def _by_year(values: pd.DataFrame) -> pd.DataFrame:
    table = values[list(HORIZON)].astype(float)
    table.loc[TOTAL] = table.sum()
    return table.loc[[TOTAL] + [f for f in table.index if f != TOTAL]]


def _scenarios(measure: str) -> Callable[[Workbook, Inputs], pd.DataFrame]:
    def build(wb: Workbook, _: Inputs) -> pd.DataFrame:
        rows = []
        for s in st.session_state.get("scenarios", []):
            r = evaluate(wb, s)
            value = {"emissions": r.scenario_emissions, "offset": r.tonnes_offset,
                     "cost": r.offset_cost}[measure]
            if value is not None:
                rows.append({"Item": s.name, "Value": value})
        return pd.DataFrame(rows, columns=["Item", "Value"])
    return build


def _items(series: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"Item": [str(i) for i in series.index], "Value": series.to_numpy()})


DATASETS = (
    Dataset("Engine quantities by year", "engines", True,
            lambda wb, x: _by_year(x.quantities)),
    Dataset("Estimated emissions by year", "tCO₂e", True,
            lambda wb, x: _by_year(x.quantities.mul(x.annual, axis=0)),
            note="Quantity × annual tCO₂e per engine."),
    Dataset("Annual tCO₂e per engine", "tCO₂e per engine", False,
            lambda wb, x: _items(x.annual)),
    Dataset("Average profit per engine per year", "USD", False,
            lambda wb, x: _items(x.profit), label_format="$,.0f",
            note="Workbook 2026 economics. Used only for the simplified teaching indicator."),
    Dataset("Carbon project prices", "USD per tCO₂e", False,
            lambda wb, x: _items(x.prices), label_format="$,.2f"),
    Dataset("Saved scenarios · scenario emissions", "tCO₂e", False, _scenarios("emissions"),
            keep_order=True),
    Dataset("Saved scenarios · tonnes offset", "tCO₂e", False, _scenarios("offset"),
            keep_order=True),
    Dataset("Saved scenarios · estimated offset cost", "USD", False, _scenarios("cost"),
            label_format="$,.0f", keep_order=True,
            note="Scenarios without a carbon project have no cost and are left out."),
)
BY_LABEL = {d.label: d for d in DATASETS}

# The workbook inputs behind each dataset, i.e. what "Use my own numbers" edits.
INPUTS_FOR = {
    "Engine quantities by year": ("quantities",),
    "Estimated emissions by year": ("quantities", "annual"),
    "Annual tCO₂e per engine": ("annual",),
    "Average profit per engine per year": ("profit",),
    "Carbon project prices": ("prices",),
}

# Per input: (title, row label, value column(s) config builder, frame <-> input converters)
_ROW_LABEL = {"quantities": "Engine family", "annual": "Engine family",
              "profit": "Engine family", "prices": "Carbon project"}
_VALUE_LABEL = {"annual": "Annual tCO₂e per engine",
                "profit": "Average profit per engine per year (USD)",
                "prices": "Price per tCO₂e (USD)"}
_TITLE = {"quantities": "Engine quantities by year", "annual": "Annual tCO₂e per engine",
          "profit": "Average profit per engine per year", "prices": "Carbon project prices"}


def _to_frame(kind: str, value) -> pd.DataFrame:
    """Input table/series -> the frame shown in the editor."""
    if kind == "quantities":
        frame = value.copy()
        frame.columns = [str(c) for c in frame.columns]
        return frame.rename_axis(_ROW_LABEL[kind]).reset_index()
    return pd.DataFrame({_ROW_LABEL[kind]: [str(i) for i in value.index],
                         _VALUE_LABEL[kind]: value.to_numpy()})


def _from_frame(kind: str, frame: pd.DataFrame, base):
    """Editor frame -> input table/series; blank cells fall back to the workbook."""
    if kind == "quantities":
        table = frame.set_index(_ROW_LABEL[kind])
        table.columns = [int(c) for c in table.columns]
        table = table.astype(float).fillna(base.astype(float))
        return table.round().clip(lower=0).astype(int).rename_axis(base.index.name)
    series = pd.Series(frame[_VALUE_LABEL[kind]].to_numpy(dtype=float),
                       index=frame[_ROW_LABEL[kind]].to_numpy())
    series = series.fillna(base)
    return series.clip(lower=0) if kind != "profit" else series


def _reset_own_numbers() -> None:
    ss = st.session_state
    ss.ex_values = {}
    ss.ex_ver = ss.get("ex_ver", 0) + 1


def _open_builder() -> None:
    st.session_state.nav = BUILDER_TAB


def _editor(kind: str, base: Inputs):
    """Editable table for one input; returns the input with the user's numbers."""
    ss = st.session_state
    values = ss.setdefault("ex_values", {})
    key = f"ex_edit_{kind}_{ss.get('ex_ver', 0)}"
    anchor_key = f"_ex_anchor_{kind}"
    if key not in ss:
        # A fresh editor (first time, or after being hidden): start from the latest numbers.
        ss[anchor_key] = values.get(kind, _to_frame(kind, getattr(base, kind)))
    anchor = ss[anchor_key]
    if kind == "quantities":
        config = {c: st.column_config.NumberColumn(c, min_value=0, max_value=9999, step=1,
                                                   format="%d", required=True)
                  for c in anchor.columns if c != _ROW_LABEL[kind]}
    else:
        money = kind in ("profit", "prices")
        config = {_VALUE_LABEL[kind]: st.column_config.NumberColumn(
            _VALUE_LABEL[kind], required=True, step=0.01 if money else 1,
            min_value=None if kind == "profit" else 0, format="dollar" if money else "localized")}
    config[_ROW_LABEL[kind]] = st.column_config.TextColumn(pinned=True)
    edited = st.data_editor(anchor, key=key, hide_index=True, width="stretch",
                            disabled=[_ROW_LABEL[kind]], column_config=config,
                            **fit_rows(len(anchor)))
    values[kind] = edited
    return _from_frame(kind, edited, getattr(base, kind))


def _change_text(found: list[tuple[str, float, float]], fmt: str) -> str:
    def show(v: float) -> str:
        if fmt.startswith("$"):
            return f"${v:,.2f}" if ".2f" in fmt else f"${v:,.0f}"
        return num(v)
    parts = [f"{where}: {show(a)} → {show(b)}" for where, a, b in found[:8]]
    more = f" and {len(found) - 8} more" if len(found) > 8 else ""
    return "; ".join(parts) + more


def _stable_colors(slot_key: str, selected: list[str]) -> dict[str, str]:
    """Give each series a colour that it keeps while it stays selected."""
    slots: dict[str, int] = st.session_state.setdefault(slot_key, {})
    for name in [n for n in slots if n not in selected]:
        del slots[name]
    for name in selected:
        if name not in slots:
            used = set(slots.values())
            slots[name] = next(i for i in range(len(SERIES)) if i not in used)
    return {name: SERIES[slots[name]] for name in selected}


def render(wb: Workbook) -> None:
    section(
        "Charts",
        "Chart the data your way",
        "Pick any data from the workbook or your saved scenarios, then show it as a bar "
        "chart or a line graph. Values are exactly as in the other tabs.",
    )

    with st.container(key="card-explore-controls"):
        pick_col, kind_col = st.columns([3, 1], vertical_alignment="bottom")
        with pick_col:
            label = st.selectbox("Data", [d.label for d in DATASETS], key="ex_data")
        with kind_col:
            kind = st.segmented_control(
                "Chart type", CHART_KINDS, key="ex_kind", default=CHART_KINDS[0],
                required=True, format_func=lambda k: {
                    "Bar": ":material/bar_chart: Bar", "Line": ":material/show_chart: Line"}[k],
            )
        ds = BY_LABEL[label]
        editable = INPUTS_FOR.get(label, ())
        own = st.toggle(
            "Use my own numbers", key="ex_own",
            help="Type over the workbook values behind this chart and see it redraw. "
                 "Your numbers are assumptions: they stay in this tab and do not change the "
                 "workbook, the other tabs or the Scenario Builder.",
        )

        base = workbook_inputs(wb)
        workbook_table = ds.build(wb, base)
        if ds.over_time:
            ids = list(workbook_table.index)
            first = HORIZON[0]
            top3 = (workbook_table.drop(index=TOTAL)[first].sort_values(ascending=False)
                    .index[:3].tolist())
            key = "ex_show_" + label
            show_col, years_col = st.columns([3, 2], vertical_alignment="bottom")
            with show_col:
                shown = st.multiselect(
                    f"Show (up to {MAX_SERIES})", ids, default=top3, key=key,
                    max_selections=MAX_SERIES,
                    help=f"'{TOTAL}' is the sum of all engine families.",
                )
            with years_col:
                start, end = st.select_slider("Years", HORIZON, value=(HORIZON[0], HORIZON[-1]),
                                              key="ex_years")

    chart_slot = st.container()

    # Own numbers: editors for the inputs behind this data, then the chart from them.
    inputs, found = base, []
    if own and editable:
        with st.container(key="card-explore-edit"):
            card_title("Your numbers",
                       "Type over any value; the chart above redraws. Blank cells use the "
                       "workbook value.")
            overrides = {}
            for input_kind in editable:
                if len(editable) > 1:
                    st.markdown(f"**{_TITLE[input_kind]}**")
                overrides[input_kind] = _editor(input_kind, base)
            st.button("Reset to workbook values", icon=":material/restart_alt:",
                      type="tertiary", on_click=_reset_own_numbers)
        inputs = with_overrides(base, overrides)
        found = [c for input_kind in editable for c in changes(base, inputs, input_kind)]
    elif own:
        with st.container(key="card-explore-edit"):
            note("Saved scenarios are changed in the Scenario Builder: pick the scenario "
                 "at the top, change it and save.")
            st.button("Open the Scenario Builder", icon=":material/edit:",
                      on_click=_open_builder)
    table = ds.build(wb, inputs)
    edited_view = bool(found)
    source_note = ("your numbers" if edited_view else
                   ("workbook forecast" if ds.over_time else "workbook values"))

    if ds.over_time:
        if not shown:
            chart_slot.info("Choose at least one engine family (or the portfolio total) to chart.")
            return
        years = [y for y in HORIZON if start <= y <= end]
        colors = _stable_colors("_ex_colors_" + label, shown)
        def to_long(t: pd.DataFrame) -> pd.DataFrame:
            return (t.loc[shown, years].rename_axis("Series").reset_index()
                    .melt(id_vars="Series", var_name="Year", value_name="Value"))

        with chart_slot, st.container(key="card-explore-chart"):
            _chart_heading(label, ds.unit, edited_view,
                           f"{'Line graph' if kind == 'Line' else 'Bar chart'} · {start}–{end} · "
                           f"{source_note}")
            charts.show(charts.multi_series(
                to_long(table), kind, colors, value_title=ds.unit, label_format=ds.label_format,
                axis_label_expr=charts.COMPACT,
                reference=to_long(workbook_table) if edited_view else None,
            ))
            _chart_notes(ds, found, kind == "Line")
        numbers = table.loc[shown, years].round(1)
        if (numbers % 1 == 0).all().all():
            numbers = numbers.astype(int)
        numbers.columns = [str(y) for y in years]
        numbers = numbers.rename_axis("Showing").reset_index()
    else:
        if table.empty:
            chart_slot.info("Save a scenario in the Scenario Builder (or restore the examples "
                            "in Compare Scenarios) to chart it here.")
            return
        with chart_slot, st.container(key="card-explore-chart"):
            _chart_heading(label, ds.unit, edited_view, f"Bar chart · one value per item · "
                                                        f"{source_note}")
            if kind == "Line":
                note("A line graph shows change over time. This data has one value per item "
                     "and no years, so it is shown as a bar chart. Pick a 'by year' dataset "
                     "to see it as a line graph.")
            reference = None
            if edited_view:
                changed = {where for where, _, _ in found}
                reference = workbook_table.set_index("Item")["Value"]
                reference = reference[reference.index.isin(changed)]
            charts.show(charts.category_bars(
                table, "Item", "Value", value_title=ds.unit, label_format=ds.label_format,
                keep_order=ds.keep_order, reference=reference,
            ))
            _chart_notes(ds, found, False)
        numbers = table.rename(columns={"Item": "Showing", "Value": ds.unit})

    with st.expander("Show the numbers", icon=":material/table_rows:"):
        st.dataframe(numbers, hide_index=True, width="stretch", **fit_rows(len(numbers)))
        st.download_button(
            "Download these numbers (CSV)", numbers.to_csv(index=False).encode("utf-8"),
            file_name=label.lower().replace(" · ", "_").replace(" ", "_") + ".csv",
            mime="text/csv", icon=":material/download:", on_click="ignore",
        )


def _chart_heading(label: str, unit: str, edited: bool, sub: str) -> None:
    card_title(f"{label} ({unit})", sub)
    if edited:
        st.html(f'<div style="margin:-.3rem 0 .4rem">{tag("asm")}</div>')


def _chart_notes(ds: Dataset, found: list, line_mode: bool) -> None:
    if found:
        mark = "Faint lines show" if line_mode else (
            "Dark ticks show" if not ds.over_time else "Switch to Line to see")
        st.caption(f"Changed from the workbook: {_change_text(found, ds.label_format)}. "
                   f"{mark} the workbook values.")
    if ds.note:
        st.caption(ds.note)
