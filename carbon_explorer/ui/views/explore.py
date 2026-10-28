"""Charts tab: show any of the app's data as a bar or line chart."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd
import streamlit as st

from ...data import HORIZON, Workbook
from ...model import evaluate
from .. import charts
from ..state import CHART_KINDS
from ..style import SERIES, card_title, fit_rows, note, section

TOTAL = "Portfolio total"
MAX_SERIES = len(SERIES)


@dataclass(frozen=True)
class Dataset:
    label: str
    unit: str            # shown in titles and tooltips
    over_time: bool      # True: one value per family per year
    build: Callable[[Workbook], pd.DataFrame]
    label_format: str = ",.0f"
    keep_order: bool = False
    note: str = ""


def _by_year(values: pd.DataFrame) -> pd.DataFrame:
    table = values[list(HORIZON)].astype(float)
    table.loc[TOTAL] = table.sum()
    return table.loc[[TOTAL] + [f for f in table.index if f != TOTAL]]


def _scenarios(measure: str) -> Callable[[Workbook], pd.DataFrame]:
    def build(wb: Workbook) -> pd.DataFrame:
        rows = []
        for s in st.session_state.get("scenarios", []):
            r = evaluate(wb, s)
            value = {"emissions": r.scenario_emissions, "offset": r.tonnes_offset,
                     "cost": r.offset_cost}[measure]
            if value is not None:
                rows.append({"Item": s.name, "Value": value})
        return pd.DataFrame(rows, columns=["Item", "Value"])
    return build


DATASETS = (
    Dataset("Engine quantities by year", "engines", True,
            lambda wb: _by_year(wb.quantities)),
    Dataset("Estimated emissions by year", "tCO₂e", True,
            lambda wb: _by_year(wb.quantities.mul(wb.emissions["annual"], axis=0)),
            note="Quantity × annual tCO₂e per engine, from the workbook forecast."),
    Dataset("Annual tCO₂e per engine", "tCO₂e per engine", False,
            lambda wb: pd.DataFrame({"Item": list(wb.families),
                                     "Value": wb.emissions["annual"].to_numpy()})),
    Dataset("Average profit per engine per year", "USD", False,
            lambda wb: pd.DataFrame({"Item": list(wb.families),
                                     "Value": wb.economics["profit"].to_numpy()}),
            label_format="$,.0f",
            note="Workbook 2026 economics. Used only for the simplified teaching indicator."),
    Dataset("Carbon project prices", "USD per tCO₂e", False,
            lambda wb: pd.DataFrame({"Item": [p.name for p in wb.projects],
                                     "Value": [p.price for p in wb.projects]}),
            label_format="$,.2f"),
    Dataset("Saved scenarios · scenario emissions", "tCO₂e", False, _scenarios("emissions"),
            keep_order=True),
    Dataset("Saved scenarios · tonnes offset", "tCO₂e", False, _scenarios("offset"),
            keep_order=True),
    Dataset("Saved scenarios · estimated offset cost", "USD", False, _scenarios("cost"),
            label_format="$,.0f", keep_order=True,
            note="Scenarios without a carbon project have no cost and are left out."),
)
BY_LABEL = {d.label: d for d in DATASETS}


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
        table = ds.build(wb)

        if ds.over_time:
            ids = list(table.index)
            first = HORIZON[0]
            top3 = table.drop(index=TOTAL)[first].sort_values(ascending=False).index[:3].tolist()
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

    if ds.over_time:
        if not shown:
            st.info("Choose at least one engine family (or the portfolio total) to chart.")
            return
        years = [y for y in HORIZON if start <= y <= end]
        colors = _stable_colors("_ex_colors_" + label, shown)
        long = (table.loc[shown, years].rename_axis("Series").reset_index()
                .melt(id_vars="Series", var_name="Year", value_name="Value"))
        with st.container(key="card-explore-chart"):
            card_title(f"{label} ({ds.unit})",
                       f"{'Line graph' if kind == 'Line' else 'Bar chart'} · {start}–{end} · "
                       "workbook forecast")
            charts.show(charts.multi_series(
                long, kind, colors, value_title=ds.unit, label_format=ds.label_format,
                axis_label_expr=charts.COMPACT,
            ))
            if ds.note:
                st.caption(ds.note)
        numbers = table.loc[shown, years].round(1)
        if (numbers % 1 == 0).all().all():
            numbers = numbers.astype(int)
        numbers.columns = [str(y) for y in years]
        numbers = numbers.rename_axis("Showing").reset_index()
    else:
        if table.empty:
            st.info("Save a scenario in the Scenario Builder (or restore the examples in "
                    "Compare Scenarios) to chart it here.")
            return
        with st.container(key="card-explore-chart"):
            card_title(f"{label} ({ds.unit})", "Bar chart · one value per item")
            if kind == "Line":
                note("A line graph shows change over time. This data has one value per item "
                     "and no years, so it is shown as a bar chart. Pick a 'by year' dataset "
                     "to see it as a line graph.")
            charts.show(charts.category_bars(
                table, "Item", "Value", value_title=ds.unit, label_format=ds.label_format,
                keep_order=ds.keep_order,
            ))
            if ds.note:
                st.caption(ds.note)
        numbers = table.rename(columns={"Item": "Showing", "Value": ds.unit})

    with st.expander("Show the numbers", icon=":material/table_rows:"):
        st.dataframe(numbers, hide_index=True, width="stretch", **fit_rows(len(numbers)))
        st.download_button(
            "Download these numbers (CSV)", numbers.to_csv(index=False).encode("utf-8"),
            file_name=label.lower().replace(" · ", "_").replace(" ", "_") + ".csv",
            mime="text/csv", icon=":material/download:", on_click="ignore",
        )
