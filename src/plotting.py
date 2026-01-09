from typing import List, Optional

import altair as alt
import pandas as pd


DEFAULT_COLORS = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F"]


def grouped_bar_chart(
    df: pd.DataFrame,
    group_label: str,
    value_field: str,
    period_order: List[str],
    value_title: Optional[str] = None,
) -> alt.Chart:
    subset = df[df["group_label"] == group_label]
    if subset.empty:
        return alt.Chart(pd.DataFrame({"node_label": [], value_field: []})).mark_bar()

    color_scale = alt.Scale(domain=period_order, range=DEFAULT_COLORS[: len(period_order)])
    value_title = value_title or value_field

    chart = (
        alt.Chart(subset)
        .mark_bar()
        .encode(
            x=alt.X("node_label:N", sort=None, title=""),
            xOffset=alt.XOffset("period_label:N", sort=period_order),
            y=alt.Y(f"{value_field}:Q", title=value_title, axis=alt.Axis(format=",.2f")),
            color=alt.Color("period_label:N", scale=color_scale),
            tooltip=[
                alt.Tooltip("period_label:N"),
                alt.Tooltip("node_label:N"),
                alt.Tooltip(f"{value_field}:Q", title=value_title, format=",.2f"),
                alt.Tooltip("tx_count:Q"),
            ],
        )
        .properties(height=320)
    )
    return chart


def node_bar_chart(
    df: pd.DataFrame,
    group_label: str,
    node_label: str,
    value_field: str,
    period_order: List[str],
    value_title: Optional[str] = None,
    show_legend: bool = True,
) -> alt.Chart:
    subset = df[(df["group_label"] == group_label) & (df["node_label"] == node_label)]
    if subset.empty:
        return alt.Chart(pd.DataFrame({"period_label": [], value_field: []})).mark_bar()

    value_title = value_title or value_field
    color_scale = alt.Scale(domain=period_order, range=DEFAULT_COLORS[: len(period_order)])
    chart = (
        alt.Chart(subset)
        .mark_bar()
        .encode(
            x=alt.X("period_label:N", sort=period_order, title=""),
            y=alt.Y(f"{value_field}:Q", title=value_title, axis=alt.Axis(format=",.2f")),
            color=alt.Color(
                "period_label:N",
                scale=color_scale,
                legend=alt.Legend(title="Period") if show_legend else None,
            ),
            tooltip=[
                alt.Tooltip("period_label:N"),
                alt.Tooltip(f"{value_field}:Q", title=value_title, format=",.2f"),
                alt.Tooltip("tx_count:Q"),
            ],
        )
        .properties(height=260)
    )
    return chart
