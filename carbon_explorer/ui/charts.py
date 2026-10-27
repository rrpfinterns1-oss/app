"""Altair charts styled to the app's tokens.

Every chart here has a table twin elsewhere on the same tab, so tooltips and
labels enhance rather than gate the values.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from .style import BASELINE, GOLD, HAIRLINE, INK, INK_2, MUTED, NAVY, SANS, STONE

_FONT = SANS.split(",")[0]
# Axis labels such as 0, 0.5M, 1M for tonne scales in the millions.
MILLIONS = "datum.value == 0 ? '0' : format(datum.value / 1e6, '.1~f') + 'M'"
# '26 instead of 2026 when ten year labels would not fit side by side.
SHORT_YEAR_WHEN_NARROW = "width < 460 ? \"'\" + slice(datum.label, 2) : datum.label"


def _finish(chart: alt.TopLevelMixin, height: int) -> alt.TopLevelMixin:
    return (
        chart.properties(height=height, background="transparent", padding={"top": 8, "right": 8, "bottom": 4, "left": 4})
        .configure(font=_FONT)
        .configure_view(stroke=None)
        .configure_axis(
            labelColor=MUTED, labelFontSize=11, labelFont=_FONT, titleColor=INK_2,
            titleFontSize=11, titleFontWeight=500, titleFont=_FONT, gridColor=HAIRLINE,
            gridWidth=1, domainColor=BASELINE, tickColor=BASELINE, labelPadding=6,
        )
        .configure_legend(
            labelColor=INK_2, labelFontSize=12, labelFont=_FONT, titleFont=_FONT,
            symbolType="square", symbolSize=110, orient="top", direction="horizontal",
            title=None, offset=4,
        )
    )


def show(chart: alt.TopLevelMixin) -> None:
    st.altair_chart(chart, theme=None, width="stretch")


def year_columns(df: pd.DataFrame, value: str, selected_year: int, *, value_title: str,
                 label_format: str, axis_format: str = ",.0f", axis_label_expr: str | None = None,
                 height: int = 230) -> alt.TopLevelMixin:
    """Columns by year, the selected year in navy and the rest in stone grey."""
    data = df.assign(Year=df["Year"].astype(str), _sel=df["Year"] == selected_year)
    base = alt.Chart(data).encode(
        x=alt.X("Year:O", title=None, scale=alt.Scale(paddingInner=0.38, paddingOuter=0.2),
                axis=alt.Axis(labelAngle=0, ticks=False, domain=True, labelOverlap=False,
                              labelExpr=SHORT_YEAR_WHEN_NARROW)),
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        y=alt.Y(f"{value}:Q", title=None, axis=alt.Axis(
            format=axis_format, labelExpr=axis_label_expr or alt.Undefined,
            tickCount=4, domain=False, ticks=False)),
        color=alt.condition("datum._sel", alt.value(NAVY), alt.value(STONE)),
        tooltip=[alt.Tooltip("Year:O"), alt.Tooltip(f"{value}:Q", title=value_title, format=label_format)],
    )
    label = base.transform_filter("datum._sel").mark_text(
        dy=-9, fontSize=12, fontWeight=500, color=INK, font=_FONT
    ).encode(y=alt.Y(f"{value}:Q"), text=alt.Text(f"{value}:Q", format=label_format))
    return _finish(bars + label, height)


def ranked_bars(df: pd.DataFrame, category: str, value: str, *, value_title: str,
                label_format: str, color: str = NAVY) -> alt.TopLevelMixin:
    """Horizontal bars sorted high to low, values labelled at the bar ends."""
    data = df[df[value] > 0]
    height = max(90, 30 * len(data))
    # Leave room on the right for the end labels.
    domain_max = float(data[value].max()) * 1.18 if len(data) else 1
    order = data.sort_values(value, ascending=False)[category].tolist()
    base = alt.Chart(data).encode(
        y=alt.Y(f"{category}:N", sort=order, title=None,
                axis=alt.Axis(ticks=False, domain=False, labelColor=INK_2, labelFontSize=12, labelLimit=180)),
        x=alt.X(f"{value}:Q", title=None, axis=None, scale=alt.Scale(domain=[0, domain_max])),
        tooltip=[alt.Tooltip(f"{category}:N"), alt.Tooltip(f"{value}:Q", title=value_title, format=label_format)],
    )
    bars = base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, size=16, color=color)
    labels = base.mark_text(align="left", dx=6, fontSize=11.5, color=INK_2, font=_FONT).encode(
        text=alt.Text(f"{value}:Q", format=label_format)
    )
    return _finish(bars + labels, height)


def coverage_by_scenario(df: pd.DataFrame, height_per_row: int = 46) -> alt.TopLevelMixin:
    """Scenario emissions split into offset / not offset, with a baseline tick.

    Expects columns: Scenario, Offset, Not offset, Baseline, Order.
    """
    long = df.melt(id_vars=["Scenario", "Order", "Baseline"], value_vars=["Offset", "Not offset"],
                   var_name="Part", value_name="tCO₂e")
    long["Stack"] = long["Part"].map({"Offset": 0, "Not offset": 1})
    order = df.sort_values("Order")["Scenario"].tolist()
    y = alt.Y("Scenario:N", sort=order, title=None,
              axis=alt.Axis(ticks=False, domain=False, labelColor=INK_2, labelFontSize=12, labelLimit=220))
    bars = alt.Chart(long).mark_bar(size=18, stroke="white", strokeWidth=2).encode(
        y=y,
        x=alt.X("sum(tCO₂e):Q", title="tCO₂e", stack="zero",
                axis=alt.Axis(labelExpr=MILLIONS, tickCount=5, domain=False, ticks=False)),
        color=alt.Color("Part:N", scale=alt.Scale(domain=["Offset", "Not offset"], range=[GOLD, NAVY]),
                        legend=alt.Legend(title=None)),
        order=alt.Order("Stack:Q"),
        tooltip=[alt.Tooltip("Scenario:N"), alt.Tooltip("Part:N"),
                 alt.Tooltip("tCO₂e:Q", format=",.0f"), alt.Tooltip("Baseline:Q", title="Baseline tCO₂e", format=",.0f")],
    )
    ticks = alt.Chart(df).mark_tick(color=INK, thickness=2, size=28).encode(
        y=y, x=alt.X("Baseline:Q"),
        tooltip=[alt.Tooltip("Scenario:N"), alt.Tooltip("Baseline:Q", title="Baseline tCO₂e", format=",.0f")],
    )
    return _finish(bars + ticks, max(120, height_per_row * len(df) + 40))


def cost_by_scenario(df: pd.DataFrame, height_per_row: int = 46) -> alt.TopLevelMixin:
    """Estimated offset cost per scenario. Expects Scenario, Cost, Order."""
    data = df.dropna(subset=["Cost"])
    y = alt.Y("Scenario:N", sort=data.sort_values("Order")["Scenario"].tolist(), title=None,
              axis=alt.Axis(ticks=False, domain=False, labelColor=INK_2, labelFontSize=12, labelLimit=220))
    domain_max = max(float(data["Cost"].max()) * 1.22, 1) if len(data) else 1
    base = alt.Chart(data).encode(
        y=y,
        x=alt.X("Cost:Q", title=None, axis=None, scale=alt.Scale(domain=[0, domain_max])),
        tooltip=[alt.Tooltip("Scenario:N"), alt.Tooltip("Cost:Q", title="Estimated offset cost (USD)", format="$,.0f")],
    )
    bars = base.mark_bar(size=18, color=GOLD, cornerRadiusTopRight=4, cornerRadiusBottomRight=4)
    labels = base.mark_text(align="left", dx=6, fontSize=11.5, color=INK_2, font=_FONT).encode(
        text=alt.Text("Cost:Q", format="$,.0f")
    )
    return _finish(bars + labels, max(120, height_per_row * len(data) + 20))
