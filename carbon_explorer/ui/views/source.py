"""Tab 5 · Source Data: every workbook value used, and how outputs are derived."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from ...data import HORIZON, WORKBOOK_PATH, Workbook
from ..style import card_title, fit_rows, note, section, tag

METHOD = (
    ("Baseline portfolio emissions",
     "Workbook quantity for the selected year × estimated annual tCO₂e per engine, summed across all engine families."),
    ("Scenario portfolio emissions",
     "User-entered scenario quantity × annual tCO₂e per engine, summed across all engine families."),
    ("Emissions change",
     "Scenario portfolio emissions − baseline portfolio emissions. Negative means lower modelled emissions."),
    ("Selected emissions",
     "Scenario emissions for only the engine families selected for offsetting."),
    ("Tonnes offset", "Selected emissions × offset percentage."),
    ("Estimated offset cost", "Tonnes offset × selected project price per tCO₂e."),
    ("Scenario interpretation",
     "Factual summary of the scenario: quantity changes, emissions change and percentage, share of "
     "scenario emissions selected, share offset and estimated cost. No preferred option."),
    ("Commercial indicator",
     "Scenario quantity × average profit per engine per year. A simplified teaching indicator."),
)

BOUNDARIES = (
    "The workbook forecast is source data. Any changed quantity is a scenario assumption.",
    "The app does not label an engine as old, inefficient or suitable for disposal; that "
    "information is not in the workbook.",
    "The app does not generate a preferred strategy or an explicit recommendation.",
    "The students' presentation contains the interpretation and conclusion.",
    "Carbon-project prices and emissions are teaching estimates.",
    "A real portfolio decision would require additional commercial, contractual and technical "
    "information.",
)


def _html_table(rows, headers) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f'<td class="txt">{escape(c)}</td>' for c in row) + "</tr>" for row in rows
    )
    return (
        '<div class="cx-table-wrap"><table class="cx-table">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    )


def render(wb: Workbook) -> None:
    section(
        "Source Data",
        "The data behind every calculation",
        f"Values below are read directly from {wb.source_name}. Scenario quantities, offset "
        "selections, the offset percentage and the carbon project are the only user assumptions.",
    )
    st.html(
        '<div class="cx-legend" style="margin:.2rem 0 1rem">'
        f"<span>{tag('src')} &nbsp;value from the workbook</span>"
        f"<span>{tag('asm')} &nbsp;entered by the user in the Scenario Builder</span>"
        f"<span>{tag('calc')} &nbsp;calculated by the app from the two</span></div>"
    )

    with st.container(key="card-src-qty"):
        card_title("Engine quantity forecast",
                   f"Portfolio sheet · engines by family and year. The app uses {HORIZON[0]}–{HORIZON[-1]}; "
                   "earlier years are shown for context only.")
        q = wb.quantities.astype(int).copy()
        q.columns = [str(c) for c in q.columns]
        q.loc["Sub-Totals (workbook)"] = [int(wb.quantity_subtotals[int(c)]) for c in q.columns]
        st.dataframe(q, width="stretch", **fit_rows(len(q)),
                     column_config={"Engine family": st.column_config.TextColumn(pinned=True)})

    with st.container(key="card-src-emissions"):
        card_title("Estimated emissions per engine", "Est.Emissions sheet · teaching estimates")
        e = wb.emissions.rename(columns={
            "per_flight": "tCO₂e per engine per flight",
            "flights": "Flights per year",
            "annual": "Annual tCO₂e per engine",
        })
        st.dataframe(e, width="stretch", **fit_rows(len(e)), column_config={
            c: st.column_config.NumberColumn(format="localized") for c in e.columns
        })
        st.caption("Annual tCO₂e per engine = tCO₂e per engine per flight × flights per year "
                   "(as calculated in the workbook).")
    with st.container(key="card-src-econ"):
        card_title(wb.economics_title, "Portfolio sheet · per engine, USD")
        ec = wb.economics.rename(columns={
            "income": "Monthly income",
            "depreciation": "Monthly depreciation",
            "interest": "Monthly interest cost",
            "profit": "Average profit per year",
        })
        st.dataframe(ec, width="stretch", **fit_rows(len(ec)), column_config={
            c: st.column_config.NumberColumn(format="dollar") for c in ec.columns
        })
        st.caption("Average profit per engine per year = (income − depreciation − interest) × 12. "
                   "Used only for the simplified commercial indicator.")

    with st.container(key="card-src-projects"):
        card_title("Carbon projects", "CO2.Credits sheet · price per tCO₂e (USD)")
        projects = pd.DataFrame([
            {"Project": p.name, "Type": p.kind, "Country": p.country or "Not stated",
             "Price per tCO₂e": p.price, "Link": p.url}
            for p in wb.projects
        ])
        st.dataframe(projects, hide_index=True, width="stretch", column_config={
            "Price per tCO₂e": st.column_config.NumberColumn(format="dollar"),
            "Link": st.column_config.LinkColumn(display_text="Project page ↗"),
        })

    with st.container(key="card-src-notes"):
        card_title("Notes on the workbook", "Observations made while reading the file")
        notes = list(wb.notes) + [
            f"Engine economics are the workbook's {wb.economics_year or 'stated'} values and are "
            "applied unchanged to every year in the commercial indicator.",
            "The workbook's Sub-Totals row for the economics table adds up per-engine figures; it is "
            "not a portfolio total and is not used by the app.",
            "Prices in the CO2.Credits sheet are formatted as US dollars and are shown to two "
            "decimal places.",
        ]
        for n in notes:
            note(n)

    with st.container(key="card-src-method"):
        card_title("How each output is calculated")
        st.html(_html_table(METHOD, ("Output", "Calculation")))

    with st.container(key="card-src-bounds"):
        card_title("Boundaries")
        for b in BOUNDARIES:
            note(b)

    st.download_button(
        "Download the source workbook", data=WORKBOOK_PATH.read_bytes(),
        file_name=WORKBOOK_PATH.name, icon=":material/download:", on_click="ignore",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
