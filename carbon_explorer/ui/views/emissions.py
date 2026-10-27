"""Tab 2 · Emissions: estimated portfolio emissions by engine family for a year."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ...data import HORIZON, Workbook
from ...fmt import num, pct, signed, signed_pct
from ...model import baseline_emissions_by_year, emissions_table
from .. import charts
from ..style import card_title, fit_rows, kpi, kpi_row, note, section, totals_table
from .portfolio import year_picker


def render(wb: Workbook) -> None:
    section(
        "Emissions",
        "Estimated portfolio emissions",
        "Each engine family's quantity × its estimated annual tCO₂e per engine "
        "(tCO₂e per engine per flight × flights per year). Emission factors are "
        "teaching estimates from the workbook.",
    )
    year = year_picker("emissions_year")

    df = emissions_table(wb, year)
    by_year = baseline_emissions_by_year(wb)
    total = float(df["Estimated tCO₂e"].sum())
    engines = int(df["Quantity"].sum())
    first = float(by_year.loc[by_year["Year"] == HORIZON[0], "Estimated tCO₂e"].iat[0])
    top = df.sort_values("Estimated tCO₂e", ascending=False).iloc[0]

    kpi_row([
        kpi("Portfolio emissions", num(total), "tCO₂e",
            sub=f"{year} · {engines:,} engines", kind="calc", accent=True),
        kpi("Average per engine", num(round(total / engines)) if engines else "n/a", "tCO₂e",
            sub="Portfolio total ÷ engines"),
        kpi(f"Change since {HORIZON[0]}", signed(total - first), "tCO₂e",
            sub=f"{signed_pct((total - first) / first)} vs {num(first)} in {HORIZON[0]}"),
        kpi("Largest family share", pct(float(top["Share of total"])),
            sub=f"{top['Engine family']} · {num(float(top['Estimated tCO₂e']))} tCO₂e"),
    ])

    left, right = st.columns([1, 1.15], gap="medium")
    with left, st.container(key="card-emissions-family"):
        card_title(f"Estimated tCO₂e by engine family, {year}", "Families with at least one engine")
        charts.show(charts.ranked_bars(df, "Engine family", "Estimated tCO₂e",
                                       value_title="Estimated tCO₂e", label_format=",.0f"))
    with right, st.container(key="card-emissions-years"):
        card_title("Estimated portfolio emissions by year",
                   f"Workbook forecast quantities · {year} highlighted")
        charts.show(charts.year_columns(
            by_year, "Estimated tCO₂e", year, value_title="Estimated tCO₂e",
            axis_label_expr=charts.MILLIONS, label_format=",.0f", height=250,
        ))
        note("Emission factors per engine are the same in every year; changes over time "
             "come only from the forecast quantities.")

    with st.container(key="card-emissions-table"):
        card_title(f"Emissions detail, {year}",
                   "Quantity and emission factors from the workbook; totals calculated by the app.")
        total_row = {
            "Engine family": "Total", "Quantity": engines,
            "Estimated tCO₂e": total, "Share of total": 1.0 if total else 0.0,
        }
        table = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)
        whole = "{:,.0f}"
        st.dataframe(
            totals_table(table, {
                "Quantity": whole, "tCO₂e per engine per flight": whole,
                "Flights per year": whole, "Annual tCO₂e per engine": whole,
                "Estimated tCO₂e": whole, "Share of total": "{:.2%}",
            }),
            hide_index=True,
            width="stretch",
            **fit_rows(len(table)), placeholder="",
            column_config={"Engine family": st.column_config.TextColumn(pinned=True)},
        )
