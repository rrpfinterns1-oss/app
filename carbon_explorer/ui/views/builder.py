"""Tab 3 · Scenario Builder: flexible assumptions in, factual results out."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from ...data import HORIZON, Workbook
from ...fmt import input_pct, num, pct, signed, signed_pct, signed_usd, usd
from ...model import Scenario, ScenarioError, evaluate, interpret
from .. import state
from ..state import FAMILY, OFFSET, SCENARIO_QTY, WORKBOOK_QTY
from ..style import (GOLD, NAVY, STONE, card_title, fit_rows, kpi, kpi_row, legend, meter, prose,
                     section, tag, totals_table)


def _step(number: str, title: str) -> None:
    st.html(
        f'<div style="display:flex;align-items:baseline;gap:.6rem;margin:.2rem 0 .1rem">'
        f'<span style="font:500 .7rem/1 Inter,sans-serif;letter-spacing:.16em;color:{GOLD}">{number}</span>'
        f'<span style="font:500 1.15rem/1.2 \'Cormorant Garamond\',Georgia,serif;color:#16191F">{title}</span>'
        "</div>"
    )


def render(wb: Workbook) -> None:
    ss = st.session_state
    section(
        "Scenario Builder",
        "Build or change a scenario",
        "Pick a saved scenario to change it, or start a new one. Change any quantity, "
        "choose which engine families to offset, then set the offset percentage and carbon "
        "project. Results recalculate as you go. Workbook values are source data; anything "
        "you change is a scenario assumption.",
    )

    names = [x.name for x in ss.scenarios]
    if ss.sb_pick != state.NEW_SCENARIO and ss.sb_pick not in names:
        ss.sb_pick, ss.sb_editing = state.NEW_SCENARIO, None
    with st.container(key="card-sb-pick"):
        pick_col, status_col = st.columns([1.1, 1], vertical_alignment="bottom")
        with pick_col:
            st.selectbox(
                "Scenario", [state.NEW_SCENARIO] + names, key="sb_pick",
                format_func=lambda n: "＋ New scenario" if n == state.NEW_SCENARIO else n,
                on_change=state.on_pick, args=(wb,),
                help="Pick a saved scenario (including examples A–D) to change it, or "
                     "start a new one from the workbook forecast.",
            )
        with status_col:
            if ss.sb_editing is None:
                status, detail = "New scenario", "not saved yet"
            elif state.has_unsaved_changes():
                status, detail = f"Changing “{ss.sb_editing}”", "unsaved changes"
            else:
                status, detail = f"Changing “{ss.sb_editing}”", "all changes saved"
            st.html(
                '<div class="cx-legend" style="padding-bottom:.55rem">'
                f'<span><i class="cx-sw" style="background:{GOLD if detail != "all changes saved" else NAVY}">'
                f"</i><b>{escape(status)}</b> · {escape(detail)}</span></div>"
            )

    left, right = st.columns([1.08, 1], gap="large")

    # ------------------------------------------------------------------ inputs
    with left, st.container(key="card-sb-inputs"):
        _step("01", "Year")
        st.select_slider(
            "Scenario year", HORIZON, key="sb_year", on_change=state.on_builder_year, args=(wb,),
            label_visibility="collapsed",
        )
        st.caption(f"Slide between {HORIZON[0]} and {HORIZON[-1]}. Changing the year reloads "
                   "that year's workbook quantities as the starting point; offset selections "
                   "are kept.")

        _step("02", "Quantities and offset selection")
        with st.container(horizontal=True, gap="small"):
            st.button("Reset quantities", icon=":material/restart_alt:", type="tertiary",
                      on_click=state.reset_quantities,
                      help="Set every scenario quantity back to the workbook forecast.")
            st.button("Select all", icon=":material/done_all:", type="tertiary",
                      on_click=state.set_selection, args=("all",))
            st.button("With engines", icon=":material/filter_list:", type="tertiary",
                      on_click=state.set_selection, args=("nonzero",),
                      help="Select only families with a scenario quantity above 0.")
            st.button("Clear", icon=":material/remove_done:", type="tertiary",
                      on_click=state.set_selection, args=("none",),
                      help="Clear the offset selection.")

        edited = st.data_editor(
            ss.sb_anchor,
            key=state.editor_key(),
            hide_index=True,
            width="stretch",
            **fit_rows(len(ss.sb_anchor)),
            disabled=[FAMILY, WORKBOOK_QTY],
            column_config={
                FAMILY: st.column_config.TextColumn(FAMILY, width=100),
                WORKBOOK_QTY: st.column_config.NumberColumn(
                    "Workbook", help=f"Source value: Portfolio sheet, {ss.sb_year}.",
                    format="%d", width=68,
                ),
                SCENARIO_QTY: st.column_config.NumberColumn(
                    "Scenario ✎", help="Your assumption. Whole numbers of 0 or more.",
                    min_value=0, max_value=999, step=1, format="%d", required=True, width=72,
                ),
                OFFSET: st.column_config.CheckboxColumn(
                    "Offset ✎", help="Include this engine family's scenario emissions "
                    "in the selected emissions to be offset.", width=62,
                ),
            },
        )
        st.html(
            '<div class="cx-legend" style="font-size:.78rem;margin-top:-.2rem">'
            f"<span>{tag('src')} &nbsp;from the workbook</span>"
            f"<span>{tag('asm')} &nbsp;editable columns marked ✎</span></div>"
        )

        _step("03", "Offset percentage and carbon project")
        st.slider("Share of selected emissions to offset", 0, 100, key="sb_offset",
                  step=1, format="%d%%")
        st.selectbox(
            "Carbon project", [p.name for p in wb.projects], key="sb_project",
            format_func=lambda name: wb.project(name).label, index=None,
            placeholder="Choose a carbon project",
        )
        if ss.sb_project:
            p = wb.project(ss.sb_project)
            link = f" · [Project page]({p.url})" if p.url else ""
            st.caption(f"{p.kind} · {p.country or 'Country not stated in workbook'} · "
                       f"workbook price ${p.price:,.2f} per tCO₂e{link}")

    quantities, blank = state.frame_quantities(edited)
    scenario = Scenario(
        name=ss.sb_name.strip() or "Unsaved scenario",
        year=int(ss.sb_year),
        quantities=quantities,
        selected=state.frame_selected(edited),
        offset_pct=float(ss.sb_offset),
        project=ss.sb_project,
    )
    try:
        r = evaluate(wb, scenario)
    except ScenarioError as exc:
        with right:
            st.error(str(exc))
        return

    # ------------------------------------------------------------------ results
    with right:
        if blank:
            st.warning("Blank scenario quantities are read as 0: " + ", ".join(blank) + ".")
        k = sum(1 for ln in r.lines if ln.selected)
        if r.offset_cost is None:
            cost_value, cost_sub = "—", "Choose a carbon project to price the offset"
        elif r.project is None:
            cost_value, cost_sub = usd(0), "Nothing to offset"
        else:
            cost_value = usd(r.offset_cost)
            cost_sub = f"{r.project.name} · ${r.project.price:,.2f}/tCO₂e"
        kpi_row([
            kpi("Baseline emissions", num(r.baseline_emissions), "tCO₂e",
                sub=f"{r.scenario.year} forecast · {r.baseline_engines:,} engines", kind="src"),
            kpi("Scenario emissions", num(r.scenario_emissions), "tCO₂e",
                sub=f"{r.scenario_engines:,} engines in scenario", kind="asm"),
            kpi("Emissions change", signed(r.emissions_change), "tCO₂e",
                sub=f"{signed_pct(r.emissions_change_pct, 2)} vs baseline · negative = lower"),
            kpi("Selected emissions", num(r.selected_emissions), "tCO₂e",
                sub=f"{k} of {r.n_families} families · {pct(r.selected_share)} of scenario"),
            kpi("Tonnes offset", num(r.tonnes_offset), "tCO₂e",
                sub=f"{input_pct(r.scenario.offset_pct)} of selected · "
                    f"{pct(r.offset_share)} of scenario"),
            kpi("Estimated offset cost", cost_value, sub=cost_sub, accent=True),
        ])

        with st.container(key="card-sb-coverage"):
            card_title("How scenario emissions are covered",
                       "Share of scenario emissions offset, selected but not offset, and not selected")
            total = r.scenario_emissions
            sel_not_offset = r.selected_emissions - r.tonnes_offset
            not_selected = total - r.selected_emissions
            if total:
                st.html(
                    meter([(GOLD, r.tonnes_offset / total), (NAVY, sel_not_offset / total),
                           (STONE, not_selected / total)])
                    + legend([
                        (GOLD, "Offset", f"{num(r.tonnes_offset)} · {pct(r.offset_share)}"),
                        (NAVY, "Selected, not offset",
                         f"{num(sel_not_offset)} · {pct(sel_not_offset / total)}"),
                        (STONE, "Not selected", f"{num(not_selected)} · {pct(not_selected / total)}"),
                    ])
                )
            else:
                st.caption("Scenario emissions are 0 tCO₂e, so there is nothing to cover.")

        with st.container(key="card-sb-interpretation"):
            card_title("Scenario interpretation",
                       "A factual summary of these assumptions. It does not recommend an option.")
            prose(interpret(r))

        kpi_row([
            kpi("Commercial indicator", usd(r.commercial_scenario),
                sub="Scenario quantity × average profit per engine per year", kind="teach"),
            kpi("Indicator change", signed_usd(r.commercial_change),
                sub=f"vs {usd(r.commercial_baseline)} for workbook quantities", kind="teach"),
        ])

        with st.container(key="card-sb-save"):
            editing = ss.sb_editing
            if editing:
                card_title("Save", f"“Save changes” updates “{editing}” everywhere in the app. "
                                   "“Save as new” keeps it and adds a copy under a new name.")
            else:
                card_title("Save for comparison",
                           "Saved scenarios appear side by side in Compare Scenarios.")
            st.text_input("Scenario name", key="sb_name", max_chars=60)
            with st.container(horizontal=True, gap="small"):
                if editing:
                    st.button("Save changes", key="sb_save_changes", icon=":material/save:",
                              type="primary",
                              on_click=state.save_changes, args=(wb,))
                    st.button("Save as new", key="sb_save_new", icon=":material/bookmark_add:",
                              on_click=state.save_as_new, args=(wb,))
                    st.button("Delete", key="sb_delete", icon=":material/delete:", type="tertiary",
                              on_click=state.delete_scenario, args=(editing,))
                else:
                    st.button("Save scenario", key="sb_save", icon=":material/bookmark_add:",
                              type="primary",
                              on_click=state.save_as_new, args=(wb,))
            flash = state.pop_flash()
            if flash:
                (st.success if flash[0] == "success" else st.error)(flash[1])

    with st.expander("Calculation detail by engine family", icon=":material/table_rows:"):
        detail = r.table()
        totals = {
            "Engine family": "Total", "Workbook qty": r.baseline_engines,
            "Scenario qty": r.scenario_engines, "Qty change": r.scenario_engines - r.baseline_engines,
            "Baseline tCO₂e": r.baseline_emissions, "Scenario tCO₂e": r.scenario_emissions,
            "Change tCO₂e": r.emissions_change, "Offset tCO₂e": r.tonnes_offset,
            "Offset cost (USD)": r.offset_cost,
        }
        detail = pd.concat([detail, pd.DataFrame([totals])], ignore_index=True)
        st.dataframe(
            totals_table(detail, {
                "Workbook qty": "{:,.0f}", "Scenario qty": "{:,.0f}", "Qty change": signed,
                "Annual tCO₂e per engine": "{:,.0f}", "Baseline tCO₂e": num,
                "Scenario tCO₂e": num, "Change tCO₂e": signed, "Offset tCO₂e": num,
                "Offset cost (USD)": lambda v: usd(v, 2),
                "Selected for offset": lambda v: "✓" if not pd.isna(v) and bool(v) else "",
            }),
            hide_index=True,
            width="stretch",
            **fit_rows(len(detail)), placeholder="",
            column_config={"Engine family": st.column_config.TextColumn(pinned=True)},
        )
        st.caption(
            "Scenario tCO₂e = scenario qty × annual tCO₂e per engine · Offset tCO₂e = "
            "scenario tCO₂e × offset % (selected families only) · Offset cost = offset "
            "tCO₂e × project price per tCO₂e."
        )
