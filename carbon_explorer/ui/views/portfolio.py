"""Tab 1 · Portfolio: workbook quantities 2026–2035 and how they progress."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ...data import HORIZON, Workbook
from ...fmt import signed
from .. import charts
from ..state import sync_year
from ..style import card_title, fit_rows, kpi, kpi_row, section


def year_picker(key: str) -> int:
    return st.segmented_control(
        "Year", HORIZON, key=key, required=True, on_change=sync_year, args=(key,),
        label_visibility="collapsed",
    )


def render(wb: Workbook) -> None:
    section(
        "Portfolio",
        f"Engine quantities, {HORIZON[0]}–{HORIZON[-1]}",
        "The workbook's engine quantity forecast by engine family. Choose a year to "
        "highlight it; the table shows the full progression.",
    )
    year = year_picker("portfolio_year")

    q = wb.quantities
    first, last = int(q[HORIZON[0]].sum()), int(q[HORIZON[-1]].sum())
    total = int(q[year].sum())
    active = int((q[year] > 0).sum())
    kpi_row([
        kpi("Engines in portfolio", f"{total:,}", sub=f"{year} workbook forecast", kind="src"),
        kpi(f"Change since {HORIZON[0]}", signed(total - first), "engines",
            sub=f"{first:,} in {HORIZON[0]} → {total:,} in {year}"),
        kpi("Engine families", str(active), f"of {len(wb.families)}",
            sub=f"with at least one engine in {year}"),
        kpi(f"{HORIZON[-1]} forecast", f"{last:,}", "engines",
            sub=f"{signed(last - first)} engines vs {HORIZON[0]}"),
    ])

    totals = pd.DataFrame({"Year": list(HORIZON), "Engines": [int(q[y].sum()) for y in HORIZON]})
    # Keep the two chart cards roughly level: the family chart grows with its rows.
    year_chart_height = max(230, 30 * active + 20)
    left, right = st.columns([1.3, 1], gap="medium")
    with left, st.container(key="card-portfolio-years"):
        card_title("Total engines by year", f"Workbook forecast · {year} highlighted")
        charts.show(charts.year_columns(
            totals, "Engines", year, value_title="Engines", label_format=",.0f",
            height=year_chart_height,
        ))
    with right, st.container(key="card-portfolio-mix"):
        card_title(f"Engines by family, {year}", "Families with at least one engine")
        mix = pd.DataFrame({"Engine family": list(wb.families), "Engines": q[year].astype(int).to_numpy()})
        charts.show(charts.ranked_bars(mix, "Engine family", "Engines", value_title="Engines",
                                       label_format=",.0f"))
        zero = [f for f in wb.families if q.at[f, year] == 0]
        if zero:
            st.caption(f"No engines in {year}: " + ", ".join(zero) + ".")

    with st.container(key="card-portfolio-table"):
        card_title("Quantity by engine family",
                   f"Workbook forecast, {HORIZON[0]}–{HORIZON[-1]}. The {year} column is highlighted.")
        table = q[list(HORIZON)].astype(int)
        table.columns = [str(y) for y in HORIZON]
        table.insert(0, "Engine family", table.index)
        # No sparkline for families with no engines in any year: a flat line
        # would read as a constant non-zero quantity.
        table["Trend"] = [
            list(map(int, row)) if row.any() else None for row in q[list(HORIZON)].to_numpy()
        ]
        table[f"Change {HORIZON[0]}→{HORIZON[-1]}"] = [
            signed(int(d)) for d in q[HORIZON[-1]] - q[HORIZON[0]]
        ]
        totals_row = {"Engine family": "Total", "Trend": [int(q[y].sum()) for y in HORIZON],
                      f"Change {HORIZON[0]}→{HORIZON[-1]}": signed(last - first)}
        totals_row.update({str(y): int(q[y].sum()) for y in HORIZON})
        table = pd.concat([table, pd.DataFrame([totals_row])], ignore_index=True)

        styled = table.style.set_properties(
            subset=[str(year)], **{"background-color": "#F7EFE1", "font-weight": "600"}
        ).set_properties(subset=pd.IndexSlice[[len(table) - 1], :], **{"font-weight": "600"})
        st.dataframe(
            styled,
            hide_index=True,
            width="stretch",
            **fit_rows(len(table)),
            column_config={
                "Engine family": st.column_config.TextColumn(pinned=True),
                "Trend": st.column_config.LineChartColumn("Trend", y_min=0, width="small"),
                f"Change {HORIZON[0]}→{HORIZON[-1]}": st.column_config.TextColumn(
                    alignment="right"),
            },
        )
