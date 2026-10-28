"""Design tokens, global CSS and small HTML building blocks."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler

# Palette. NAVY and GOLD are the two chart series colours; both pass the
# dataviz palette validator (lightness band, chroma floor, CVD separation and
# 3:1 contrast) on the white card surface.
PAGE = "#F6F4EF"
SURFACE = "#FFFFFF"
INK = "#16191F"
INK_2 = "#4E525C"
MUTED = "#86837C"
HAIRLINE = "#E9E5DC"
BASELINE = "#CFC9BD"
NAVY = "#34538F"
GOLD = "#B38236"
STONE = "#DDD7CC"  # de-emphasis grey for context marks
# Up to six series in one chart, in this fixed order. Passes the dataviz palette
# validator on white (adjacent colour-blind separation >= 8, normal >= 15).
SERIES = ("#34538F", "#B38236", "#008F83", "#C16048", "#7B63A3", "#69954F")
DEEP = "#1F2E4D"

SANS = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
SERIF = "'Cormorant Garamond', Georgia, 'Times New Roman', serif"

_CSS = f"""
<style>
:root {{
  --page: {PAGE}; --surface: {SURFACE}; --ink: {INK}; --ink-2: {INK_2};
  --muted: {MUTED}; --hairline: {HAIRLINE}; --navy: {NAVY}; --gold: {GOLD};
  --stone: {STONE}; --deep: {DEEP};
}}
[data-testid="stDecoration"], [data-testid="stAppDeployButton"], #MainMenu,
footer {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{
  max-width: 1240px; padding-top: 2.6rem; padding-bottom: 4rem;
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding-left: 1rem; padding-right: 1rem; padding-top: 1.6rem; }}
}}

/* Tabs: quiet, letter-spaced labels with a fine gold indicator */
[data-testid="stTabs"] [role="tablist"] {{ gap: 1.9rem; border-bottom: 1px solid var(--hairline); }}
[data-testid="stTab"] {{ padding: 0.55rem 0 0.85rem; background: transparent; }}
[data-testid="stTab"] p {{
  font-size: 0.74rem; letter-spacing: 0.14em; text-transform: uppercase; font-weight: 500;
  color: var(--muted); white-space: nowrap;
}}
[data-testid="stTab"]:hover p {{ color: var(--ink-2); }}
[data-testid="stTab"][aria-selected="true"] p {{ color: var(--ink); }}
[data-testid="stTab"][aria-selected="true"] > div[data-rac] {{ background-color: var(--gold) !important; }}

/* Cards: any container whose key starts with "card" */
div[class*="st-key-card"] {{
  background: var(--surface); border: 1px solid var(--hairline); border-radius: 14px;
  padding: 1.4rem 1.5rem 1.3rem; box-shadow: 0 1px 2px rgba(22,25,31,0.03);
}}
@media (max-width: 640px) {{ div[class*="st-key-card"] {{ padding: 1.1rem 1rem; }} }}

h1, h2, h3 {{ letter-spacing: -0.01em; }}
[data-testid="stCaptionContainer"] {{ color: var(--muted); }}
[data-testid="stButtonGroup"] button {{ padding-left: 0.72rem; padding-right: 0.72rem; }}
[data-testid="stExpander"] details {{ background: var(--surface); border-color: var(--hairline); }}

/* Custom HTML blocks */
.cx-hero {{ margin: 0 0 1.6rem; }}
.cx-eyebrow {{
  font: 500 0.72rem/1 {SANS}; letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--gold); margin-bottom: 0.9rem;
}}
.cx-hero h1 {{
  font: 500 clamp(2.3rem, 4.4vw, 3.4rem)/1.04 {SERIF}; color: var(--ink);
  margin: 0; padding: 0; letter-spacing: -0.015em;
}}
.cx-rule {{ width: 56px; height: 1px; background: var(--gold); margin: 1.1rem 0 0.9rem; }}
.cx-hero p {{ font: 400 0.98rem/1.6 {SANS}; color: var(--ink-2); max-width: 720px; margin: 0; }}
.cx-meta {{ display: flex; flex-wrap: wrap; gap: 0.4rem 1.2rem; margin-top: 0.9rem;
  font: 400 0.78rem/1.4 {SANS}; color: var(--muted); }}
.cx-meta span::before {{ content: "◆"; color: var(--gold); font-size: 0.5rem; margin-right: 0.45rem; vertical-align: 2px; }}

.cx-section {{ margin: 0.6rem 0 0.2rem; }}
.cx-section .k {{ font: 500 0.68rem/1 {SANS}; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); }}
.cx-section h2 {{ font: 500 1.75rem/1.15 {SERIF}; color: var(--ink); margin: 0.35rem 0 0.25rem; padding: 0; }}
.cx-section p {{ font: 400 0.9rem/1.55 {SANS}; color: var(--ink-2); margin: 0; max-width: 780px; }}

.cx-card-title {{ font: 500 1.2rem/1.2 {SERIF}; color: var(--ink); margin: 0 0 0.15rem; }}
.cx-card-sub {{ font: 400 0.8rem/1.45 {SANS}; color: var(--muted); margin: 0 0 0.6rem; }}

.cx-kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 0.2rem 0 0.4rem; }}
.cx-kpi {{ background: var(--surface); border: 1px solid var(--hairline); border-radius: 14px; padding: 1rem 1.1rem 0.95rem; }}
.cx-kpi .l {{ display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.3rem 0.5rem;
  font: 500 0.68rem/1.3 {SANS}; letter-spacing: 0.1em; text-transform: uppercase; color: var(--muted); }}
.cx-kpi .v {{ font: 500 1.55rem/1.15 {SANS}; color: var(--ink); margin-top: 0.55rem; letter-spacing: -0.015em; white-space: nowrap; }}
.cx-kpi .v small {{ font-size: 0.78rem; font-weight: 400; color: var(--muted); letter-spacing: 0; margin-left: 0.2rem; }}
.cx-kpi .s {{ font: 400 0.78rem/1.45 {SANS}; color: var(--ink-2); margin-top: 0.35rem; }}
.cx-kpi.accent {{ border-color: #E4D3B5; background: linear-gradient(180deg, #FFFDF8, #FFFFFF); }}

.cx-tag {{ display: inline-block; font: 500 0.6rem/1 {SANS}; letter-spacing: 0.1em; text-transform: uppercase;
  padding: 0.28rem 0.45rem; border-radius: 999px; white-space: nowrap; }}
.cx-tag.src {{ background: #EBEFF6; color: #2B4170; }}
.cx-tag.asm {{ background: #F5EEDF; color: #765622; }}
.cx-tag.calc, .cx-tag.teach {{ background: #F1EFEA; color: #55524B; }}

.cx-legend {{ display: flex; flex-wrap: wrap; gap: 0.5rem 1.4rem; font: 400 0.82rem/1.4 {SANS}; color: var(--ink-2); }}
.cx-legend b {{ font-weight: 500; color: var(--ink); }}
.cx-sw {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 0.45rem; vertical-align: -1px; }}

.cx-meter {{ display: flex; gap: 2px; height: 14px; border-radius: 7px; overflow: hidden; background: var(--hairline); margin: 0.5rem 0 0.9rem; }}
.cx-meter div {{ height: 100%; }}

.cx-prose p {{ font: 400 0.95rem/1.7 {SANS}; color: var(--ink); margin: 0 0 0.7rem; }}
.cx-prose p:last-child {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 0; }}

.cx-note {{ border-left: 2px solid var(--gold); padding: 0.2rem 0 0.2rem 0.9rem; font: 400 0.84rem/1.55 {SANS}; color: var(--ink-2); margin: 0.4rem 0; }}

.cx-table-wrap {{ overflow-x: auto; border: 1px solid var(--hairline); border-radius: 14px; background: var(--surface); }}
.cx-table {{ border-collapse: collapse; width: 100%; font: 400 0.84rem/1.45 {SANS}; color: var(--ink); }}
.cx-table th, .cx-table td {{ padding: 0.62rem 0.9rem; border-bottom: 1px solid var(--hairline); text-align: left; vertical-align: top; }}
.cx-table thead th {{ font: 500 1rem/1.25 {SERIF}; color: var(--ink); background: #FBFAF7; border-bottom: 1px solid #DCD6CA; }}
.cx-table td.num, .cx-table th.num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.cx-table td.muted {{ color: var(--ink-2); }}
.cx-table td.grpcell {{ border-right: 1px solid var(--hairline); background: #FDFCF9; }}
.cx-table tr:last-child td {{ border-bottom: 0; }}
.cx-table.compare th:first-child, .cx-table.compare td:first-child {{ color: var(--ink-2); position: sticky; left: 0; background: var(--surface); min-width: 210px; }}
.cx-table.compare thead th {{ min-width: 170px; text-align: right; }}
.cx-table.compare thead th:first-child {{ background: #FBFAF7; text-align: left; }}
.cx-table.compare thead th .ill {{ display: block; font: 500 0.6rem/1.2 {SANS}; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); margin-top: 0.25rem; }}
.cx-table.compare tr.grp td {{ font: 500 0.66rem/1 {SANS}; letter-spacing: 0.16em; text-transform: uppercase; color: var(--gold); background: #FDFCF9; padding-top: 0.9rem; }}
.cx-table.compare td.txt {{ max-width: 280px; }}

.cx-status {{ display: inline-flex; align-items: center; gap: 0.35rem; font: 500 0.8rem/1 {SANS}; white-space: nowrap; }}
.cx-status.ok {{ color: #1D6B1D; }}
.cx-status.bad {{ color: #B42F2F; }}

.cx-footer {{ margin-top: 3rem; padding-top: 1.2rem; border-top: 1px solid var(--hairline);
  font: 400 0.78rem/1.6 {SANS}; color: var(--muted); }}
</style>
"""


def inject_css() -> None:
    st.html(_CSS)


def tag(kind: str) -> str:
    label = {"src": "Workbook", "asm": "Assumption", "calc": "Calculated",
             "teach": "Teaching"}[kind]
    return f'<span class="cx-tag {kind}">{label}</span>'


def hero(eyebrow: str, title: str, body: str, meta: list[str]) -> None:
    st.html(
        '<div class="cx-hero">'
        f'<div class="cx-eyebrow">{escape(eyebrow)}</div>'
        f"<h1>{escape(title)}</h1>"
        '<div class="cx-rule"></div>'
        f"<p>{escape(body)}</p>"
        '<div class="cx-meta">' + "".join(f"<span>{escape(m)}</span>" for m in meta) + "</div>"
        "</div>"
    )


def section(kicker: str, title: str, body: str = "") -> None:
    st.html(
        '<div class="cx-section">'
        f'<div class="k">{escape(kicker)}</div>'
        f"<h2>{escape(title)}</h2>"
        + (f"<p>{escape(body)}</p>" if body else "")
        + "</div>"
    )


def card_title(title: str, sub: str = "") -> None:
    st.html(
        f'<div class="cx-card-title">{escape(title)}</div>'
        + (f'<div class="cx-card-sub">{escape(sub)}</div>' if sub else "")
    )


def kpi(label: str, value: str, unit: str = "", sub: str = "", kind: str | None = None,
        accent: bool = False) -> str:
    """One KPI tile as HTML. Values are proportional (not tabular) figures."""
    return (
        f'<div class="cx-kpi{" accent" if accent else ""}">'
        f'<div class="l"><span>{escape(label)}</span>{tag(kind) if kind else ""}</div>'
        f'<div class="v">{escape(value)}'
        + (f"<small>{escape(unit)}</small>" if unit else "")
        + "</div>"
        + (f'<div class="s">{escape(sub)}</div>' if sub else "")
        + "</div>"
    )


def kpi_row(tiles: list[str]) -> None:
    st.html('<div class="cx-kpis">' + "".join(tiles) + "</div>")


def note(text: str) -> None:
    st.html(f'<div class="cx-note">{escape(text)}</div>')


def prose(paragraphs: list[str]) -> None:
    st.html('<div class="cx-prose">' + "".join(f"<p>{escape(p)}</p>" for p in paragraphs) + "</div>")


def legend(items: list[tuple[str, str, str]]) -> str:
    """(colour, label, value) swatches."""
    return '<div class="cx-legend">' + "".join(
        f'<span><i class="cx-sw" style="background:{c}"></i>{escape(label)} <b>{escape(v)}</b></span>'
        for c, label, v in items
    ) + "</div>"


def meter(segments: list[tuple[str, float]]) -> str:
    """A 100% bar from (colour, fraction) segments; zero-width segments are dropped."""
    return '<div class="cx-meter">' + "".join(
        f'<div style="flex:{f:.6f} 1 0;background:{c}"></div>' for c, f in segments if f > 0
    ) + "</div>"


def status(passed: bool) -> str:
    return (
        '<span class="cx-status ok">✓ Pass</span>'
        if passed
        else '<span class="cx-status bad">✕ Fail</span>'
    )


ROW_HEIGHT = 34


def fit_rows(rows: int) -> dict:
    """st.dataframe / st.data_editor sizing that shows every row without scrolling."""
    return {"row_height": ROW_HEIGHT, "height": ROW_HEIGHT * (rows + 1) + 2}


def totals_table(df: pd.DataFrame, formats: dict) -> Styler:
    """Format columns explicitly, blank out missing cells and bold the last (total) row."""
    return df.style.format(formats, na_rep="").set_properties(
        subset=pd.IndexSlice[[df.index[-1]], :], **{"font-weight": "600"}
    )


def footer(text: str) -> None:
    st.html(f'<div class="cx-footer">{escape(text)}</div>')
