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
COMPACT = ("datum.value >= 1e6 ? format(datum.value / 1e6, '.2~f') + 'M' : "
           "datum.value >= 1e3 ? format(datum.value / 1e3, ',.0f') + 'k' : format(datum.value, ',')")
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


def year_line(df: pd.DataFrame, value: str, selected_year: int, *, value_title: str,
              label_format: str, axis_format: str = ",.0f", axis_label_expr: str | None = None,
              height: int = 230) -> alt.TopLevelMixin:
    """A single series over time; the selected year's point is filled and labelled."""
    data = df.assign(Year=df["Year"].astype(str), _sel=df["Year"] == selected_year)
    base = alt.Chart(data).encode(
        x=alt.X("Year:O", title=None, scale=alt.Scale(padding=0.5),
                axis=alt.Axis(labelAngle=0, ticks=False, domain=True, labelOverlap=False,
                              labelExpr=SHORT_YEAR_WHEN_NARROW)),
        y=alt.Y(f"{value}:Q", title=None, scale=alt.Scale(zero=False, nice=True),
                axis=alt.Axis(format=axis_format, labelExpr=axis_label_expr or alt.Undefined,
                              tickCount=4, domain=False, ticks=False)),
    )
    tooltip = [alt.Tooltip("Year:O"), alt.Tooltip(f"{value}:Q", title=value_title, format=label_format)]
    line = base.mark_line(color=NAVY, strokeWidth=2)
    dots = base.mark_point(filled=True, stroke=NAVY, strokeWidth=2).encode(
        fill=alt.condition("datum._sel", alt.value(NAVY), alt.value("white")),
        size=alt.condition("datum._sel", alt.value(110), alt.value(40)),
    )
    # Invisible, generous hover targets so the tooltip is easy to reach.
    hits = base.mark_point(size=600, opacity=0).encode(tooltip=tooltip)
    label = base.transform_filter("datum._sel").mark_text(
        dy=-15, fontSize=12, fontWeight=500, color=INK, font=_FONT
    ).encode(text=alt.Text(f"{value}:Q", format=label_format))
    return _finish(line + dots + label + hits, height)


def family_lines(df: pd.DataFrame, value: str, focus: str, selected_year: int, *,
                 value_title: str, label_format: str, axis_format: str = ",.0f",
                 axis_label_expr: str | None = None, height: int = 290) -> alt.TopLevelMixin:
    """Every engine family over time in grey with one highlighted in navy.

    Expects long data with columns Engine family, Year and the value column.
    """
    data = df.assign(Year=df["Year"].astype(str))
    x = alt.X("Year:O", title=None, scale=alt.Scale(padding=0.5),
              axis=alt.Axis(labelAngle=0, ticks=False, domain=True, labelOverlap=False,
                            labelExpr=SHORT_YEAR_WHEN_NARROW))
    y = alt.Y(f"{value}:Q", title=None,
              axis=alt.Axis(format=axis_format, labelExpr=axis_label_expr or alt.Undefined,
                            tickCount=4, domain=False, ticks=False))
    is_focus = data["Engine family"] == focus
    others = alt.Chart(data[~is_focus]).mark_line(color=STONE, strokeWidth=1.5).encode(
        x=x, y=y, detail="Engine family:N")
    focus_data = data[is_focus]
    focus_line = alt.Chart(focus_data).mark_line(color=NAVY, strokeWidth=2.5).encode(x=x, y=y)
    focus_dots = alt.Chart(focus_data).mark_point(filled=True, color=NAVY, size=36).encode(x=x, y=y)
    label = alt.Chart(focus_data[focus_data["Year"] == str(selected_year)]).mark_text(
        dy=-14, fontSize=12, fontWeight=500, color=INK, font=_FONT
    ).encode(x=x, y=y, text=alt.Text(f"{value}:Q", format=label_format))
    marker = alt.Chart(pd.DataFrame({"Year": [str(selected_year)]})).mark_rule(
        color=GOLD, strokeWidth=1, opacity=0.8).encode(x=x)
    hits = alt.Chart(data).mark_point(size=300, opacity=0).encode(
        x=x, y=y,
        tooltip=[alt.Tooltip("Engine family:N"), alt.Tooltip("Year:O"),
                 alt.Tooltip(f"{value}:Q", title=value_title, format=label_format)],
    )
    return _finish(marker + others + focus_line + focus_dots + label + hits, height)


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


def multi_series(long: pd.DataFrame, kind: str, colors: dict[str, str], *, value_title: str,
                 label_format: str, axis_label_expr: str | None = None,
                 reference: pd.DataFrame | None = None, height: int = 340) -> alt.TopLevelMixin:
    """Several series across the years, as lines or grouped bars.

    Expects long data with columns Series, Year and Value; `colors` maps each
    series to its colour and sets the legend order. `reference` (same shape)
    is drawn as faint lines in line mode, e.g. the workbook values behind
    user-edited numbers.
    """
    names = list(colors)
    data = long.assign(Year=long["Year"].astype(str))
    color = alt.Color("Series:N", scale=alt.Scale(domain=names, range=[colors[n] for n in names]),
                      legend=alt.Legend(title=None, labelLimit=220, columns=3, symbolOpacity=1))
    x = alt.X("Year:O", title=None, scale=alt.Scale(padding=0.5 if kind == "Line" else 0.1),
              axis=alt.Axis(labelAngle=0, ticks=False, domain=True, labelOverlap=False,
                            labelExpr=SHORT_YEAR_WHEN_NARROW))
    y = alt.Y("Value:Q", title=None,
              axis=alt.Axis(format=",.0f", labelExpr=axis_label_expr or alt.Undefined,
                            tickCount=5, domain=False, ticks=False))
    tooltip = [alt.Tooltip("Series:N", title="Showing"), alt.Tooltip("Year:O"),
               alt.Tooltip("Value:Q", title=value_title, format=label_format)]
    base = alt.Chart(data)
    if kind == "Line":
        chart = (
            base.mark_line(strokeWidth=2).encode(x=x, y=y, color=color)
            + base.mark_point(filled=True, size=40).encode(x=x, y=y, color=color)
            + base.mark_point(size=400, opacity=0).encode(x=x, y=y, tooltip=tooltip)
        )
        if reference is not None:
            ref = alt.Chart(reference.assign(Year=reference["Year"].astype(str)))
            ref_tip = [alt.Tooltip("Series:N", title="Workbook"), alt.Tooltip("Year:O"),
                       alt.Tooltip("Value:Q", title=value_title, format=label_format)]
            chart = (ref.mark_line(strokeWidth=1.5, opacity=0.35).encode(x=x, y=y, color=color)
                     + ref.mark_point(size=200, opacity=0).encode(x=x, y=y, tooltip=ref_tip)
                     + chart)
    else:
        chart = base.mark_bar(stroke="white", strokeWidth=1, cornerRadiusTopLeft=3,
                              cornerRadiusTopRight=3).encode(
            x=x, xOffset=alt.XOffset("Series:N", sort=names), y=y, color=color, tooltip=tooltip)
    return _finish(chart, height)


def category_bars(df: pd.DataFrame, category: str, value: str, *, value_title: str,
                  label_format: str, keep_order: bool = False, color: str = NAVY,
                  reference: pd.Series | None = None) -> alt.TopLevelMixin:
    """Horizontal bars for one value per category; handles negative values.

    `reference` (category -> value) adds a dark tick at that value, e.g. the
    workbook value behind a user-edited number.
    """
    data = df.copy()
    if reference is not None:
        data["_ref"] = data[category].map(reference)
        ref_values = data["_ref"].dropna()
    else:
        ref_values = pd.Series(dtype=float)
    order = data[category].tolist() if keep_order else (
        data.sort_values(value, ascending=False)[category].tolist())
    every = pd.concat([data[value], ref_values])
    lo, hi = min(0.0, float(every.min())), max(0.0, float(every.max()))
    pad = (hi - lo) * 0.2 or 1
    data["_neg"] = data[value] < 0
    base = alt.Chart(data).encode(
        y=alt.Y(f"{category}:N", sort=order, title=None,
                axis=alt.Axis(ticks=False, domain=False, labelColor=INK_2, labelFontSize=12,
                              labelLimit=220)),
        x=alt.X(f"{value}:Q", title=None, axis=None,
                scale=alt.Scale(domain=[lo - (pad if lo < 0 else 0), hi + pad])),
        tooltip=[alt.Tooltip(f"{category}:N"),
                 alt.Tooltip(f"{value}:Q", title=value_title, format=label_format)],
    )
    bars = base.mark_bar(size=16, color=color, cornerRadius=3)
    pos = base.transform_filter("!datum._neg").mark_text(
        align="left", dx=6, fontSize=11.5, color=INK_2, font=_FONT
    ).encode(text=alt.Text(f"{value}:Q", format=label_format))
    neg = base.transform_filter("datum._neg").mark_text(
        align="right", dx=-6, fontSize=11.5, color=INK_2, font=_FONT
    ).encode(text=alt.Text(f"{value}:Q", format=label_format))
    zero = alt.Chart(pd.DataFrame({"z": [0]})).mark_rule(color=BASELINE).encode(
        x=alt.X("z:Q", axis=None))
    layers = zero + bars + pos + neg
    if len(ref_values):
        ticks = alt.Chart(data.dropna(subset=["_ref"])).mark_tick(
            color=INK, thickness=2, size=22).encode(
            y=alt.Y(f"{category}:N", sort=order), x=alt.X("_ref:Q"),
            tooltip=[alt.Tooltip(f"{category}:N"),
                     alt.Tooltip("_ref:Q", title="Workbook value", format=label_format)])
        layers = layers + ticks
    return _finish(layers, max(120, 30 * len(data) + 10))


def paired_bars(df: pd.DataFrame, *, value_title: str, label_format: str) -> alt.TopLevelMixin:
    """Workbook vs scenario value per engine family, side by side.

    Expects columns Engine family, Series ("Workbook forecast" / "Your scenario")
    and Value; families are ordered by the scenario value.
    """
    names = ["Workbook forecast", "Your scenario"]
    order = (df[df["Series"] == names[1]].sort_values("Value", ascending=False)
             ["Engine family"].tolist())
    chart = alt.Chart(df).mark_bar(size=9, cornerRadiusTopRight=3,
                                   cornerRadiusBottomRight=3).encode(
        y=alt.Y("Engine family:N", sort=order, title=None,
                axis=alt.Axis(ticks=False, domain=False, labelColor=INK_2, labelFontSize=12)),
        yOffset=alt.YOffset("Series:N", sort=names),
        x=alt.X("Value:Q", title=None,
                axis=alt.Axis(labelExpr=COMPACT, tickCount=4, domain=False, ticks=False)),
        color=alt.Color("Series:N", scale=alt.Scale(domain=names, range=[STONE, NAVY]),
                        legend=alt.Legend(title=None)),
        tooltip=[alt.Tooltip("Engine family:N"), alt.Tooltip("Series:N", title="Showing"),
                 alt.Tooltip("Value:Q", title=value_title, format=label_format)],
    )
    return _finish(chart, max(140, 30 * df["Engine family"].nunique() + 40))


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
