"""Tab 7 · Findings: a notes workspace. The app never writes findings itself."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape

import pandas as pd
import streamlit as st

from ...data import Workbook
from ...model import evaluate, summary
from ..style import section

NONE = "None"


def _markdown(wb: Workbook, notes: list[dict]) -> str:
    ss = st.session_state
    by_name = {s.name: s for s in ss.scenarios}
    lines = ["# Scenario findings", "",
             f"Notes written by the project team. Source data: {wb.source_name}. "
             "Figures are teaching estimates.", ""]
    for n in notes:
        lines += [f"## {n['title'] or 'Untitled note'}", f"_{n['created']}_", ""]
        if n["scenario"] != NONE:
            lines.append(f"Related scenario: **{n['scenario']}**")
            s = by_name.get(n["scenario"])
            if s is not None:
                lines += ["", "| Measure | Value |", "| --- | --- |"]
                lines += [f"| {label} | {text} |" for _, label, _, text in summary(evaluate(wb, s))]
            else:
                lines.append("(scenario no longer saved)")
            lines.append("")
        lines += [n["text"], ""]
    return "\n".join(lines)


def render(wb: Workbook) -> None:
    ss = st.session_state
    section(
        "Findings",
        "Analyst notes",
        "Capture your own observations from the scenarios. The app does not generate findings "
        "or recommendations; everything here is written by you. Notes last for this browser "
        "session, so export them before closing.",
    )

    left, right = st.columns([1, 1.2], gap="large")
    with left, st.container(key="card-notes-form"):
        with st.form("note_form", clear_on_submit=True, border=False):
            title = st.text_input("Title (optional)", max_chars=120)
            scenario = st.selectbox("Related scenario (optional)",
                                    [NONE] + [s.name for s in ss.scenarios])
            text = st.text_area("Observation", height=160,
                                placeholder="What did you notice in the numbers?")
            if st.form_submit_button("Add note", icon=":material/note_add:", type="primary"):
                if text.strip():
                    ss.notes.append({
                        "title": title.strip(), "scenario": scenario, "text": text.strip(),
                        "created": datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC"),
                    })
                else:
                    st.warning("Write an observation before adding the note.")

    with right:
        if not ss.notes:
            st.caption("No notes yet.")
        for i, n in enumerate(ss.notes):
            with st.container(key=f"card-note-{i}"):
                meta = n["created"] + (f" · {n['scenario']}" if n["scenario"] != NONE else "")
                st.html(
                    f'<div class="cx-card-title">{escape(n["title"] or "Untitled note")}</div>'
                    f'<div class="cx-card-sub">{escape(meta)}</div>'
                    f'<div class="cx-prose"><p style="color:#16191F;font-size:.92rem">'
                    f'{escape(n["text"]).replace(chr(10), "<br>")}</p></div>'
                )
                st.button("Delete", key=f"note_del_{i}", icon=":material/delete:", type="tertiary",
                          on_click=lambda i=i: ss.notes.pop(i))
        if ss.notes:
            with st.container(horizontal=True, gap="small"):
                st.download_button(
                    "Export notes (Markdown)", data=_markdown(wb, ss.notes).encode("utf-8"),
                    file_name="findings.md", mime="text/markdown", icon=":material/description:",
                    on_click="ignore",
                )
                st.download_button(
                    "Export notes (CSV)",
                    data=pd.DataFrame(ss.notes)[["created", "title", "scenario", "text"]]
                    .to_csv(index=False).encode("utf-8"),
                    file_name="findings.csv", mime="text/csv", icon=":material/table_view:",
                    on_click="ignore",
                )
