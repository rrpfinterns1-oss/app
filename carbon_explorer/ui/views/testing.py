"""Tab 6 · Testing: the recorded calculation tests and workbook checks."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import pandas as pd
import streamlit as st

from ...checks import integrity_checks, run_model_cases
from ...data import HORIZON, Workbook
from ...fmt import num
from ..style import card_title, fit_rows, kpi, kpi_row, section, status, totals_table


def render(wb: Workbook) -> None:
    section(
        "Testing",
        "Recorded tests",
        "Each test runs the app's calculations against a value worked out by hand from the "
        "workbook. The tests re-run every time this page loads; the same cases run in the "
        "automated test suite (pytest).",
    )
    outcomes = run_model_cases(wb)
    checks = integrity_checks(wb)
    run_at = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    passed = sum(o.passed for o in outcomes)
    ok = sum(c.passed for c in checks)
    cases = len({o.case_id for o in outcomes})
    kpi_row([
        kpi("Calculation tests", f"{passed} / {len(outcomes)}", "pass",
            sub=f"{cases} test cases · manual calculation, year change, quantity change, "
                "targeted selection, zero offset and more"),
        kpi("Workbook checks", f"{ok} / {len(checks)}", "pass",
            sub="Sub-totals, emission factors, economics, families, projects"),
        kpi("Last run", run_at.split(",")[0], sub=run_at.split(", ")[1]),
    ])

    with st.container(key="card-test-cases"):
        card_title("Calculation tests", "Expected values are calculated by hand; the working is shown.")
        rows = []
        for case_id in dict.fromkeys(o.case_id for o in outcomes):
            group = [o for o in outcomes if o.case_id == case_id]
            for i, o in enumerate(group):
                lead = (
                    f'<td class="grpcell" rowspan="{len(group)}"><b>{escape(o.case_id)}</b> '
                    f'{escape(o.case)}<br><span style="color:#86837C">{escape(o.inputs)}</span></td>'
                    if i == 0 else ""
                )
                rows.append(
                    f"<tr>{lead}<td>{escape(o.metric)}</td>"
                    f'<td class="muted">{escape(o.working)}</td>'
                    f'<td class="num">{escape(o.expected)}</td>'
                    f'<td class="num">{escape(o.actual)}</td>'
                    f"<td>{status(o.passed)}</td></tr>"
                )
        st.html(
            '<div class="cx-table-wrap"><table class="cx-table"><thead><tr>'
            "<th>Test and inputs</th><th>Measure</th><th>Manual working</th>"
            '<th class="num">Expected</th><th class="num">App result</th><th>Status</th>'
            f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        )

    left, right = st.columns([1, 1], gap="medium")
    with left, st.container(key="card-test-manual"):
        y = HORIZON[0]
        card_title(f"Manual calculation, {y} baseline",
                   "Quantity × annual tCO₂e per engine, family by family")
        q = wb.quantities_for(y)
        manual = pd.DataFrame({
            "Engine family": list(wb.families),
            "Quantity": [q[f] for f in wb.families],
            "Annual tCO₂e per engine": [wb.annual_tco2e(f) for f in wb.families],
        })
        manual["tCO₂e"] = manual["Quantity"] * manual["Annual tCO₂e per engine"]
        total = manual["tCO₂e"].sum()
        manual = pd.concat([manual, pd.DataFrame([{
            "Engine family": "Total", "Quantity": int(manual["Quantity"].sum()), "tCO₂e": total,
        }])], ignore_index=True)
        st.dataframe(
            totals_table(manual, {"Quantity": "{:,.0f}", "Annual tCO₂e per engine": "{:,.0f}",
                                  "tCO₂e": "{:,.0f}"}),
            hide_index=True, width="stretch", **fit_rows(len(manual)), placeholder="",
        )
        st.caption(f"Total {num(total)} tCO₂e; test T-01 checks the app returns the same figure.")

    with right, st.container(key="card-test-integrity"):
        card_title("Workbook checks", "Confirms the workbook's own figures are consistent")
        rows = "".join(
            f"<tr><td><b>{escape(c.id)}</b> {escape(c.name)}</td>"
            f'<td class="muted">{escape(c.detail)}</td>'
            f"<td>{status(c.passed)}</td></tr>"
            for c in checks
        )
        st.html(
            '<div class="cx-table-wrap"><table class="cx-table"><thead><tr>'
            "<th>Check</th><th>Detail</th><th>Status</th>"
            f"</tr></thead><tbody>{rows}</tbody></table></div>"
        )

    record = pd.DataFrame(
        [{"Run (UTC)": run_at, "Type": "Calculation", "ID": o.case_id, "Test": o.case,
          "Inputs": o.inputs, "Measure": o.metric, "Manual working": o.working,
          "Expected": o.expected, "App result": o.actual, "Result": "Pass" if o.passed else "Fail"}
         for o in outcomes]
        + [{"Run (UTC)": run_at, "Type": "Workbook check", "ID": c.id, "Test": c.name,
            "Inputs": wb.source_name, "Measure": c.detail, "Manual working": "", "Expected": "",
            "App result": "", "Result": "Pass" if c.passed else "Fail"}
           for c in checks]
    )
    st.download_button(
        "Download test record (CSV)", data=record.to_csv(index=False).encode("utf-8"),
        file_name="test_record.csv", mime="text/csv", icon=":material/download:", on_click="ignore",
    )
