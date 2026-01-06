from typing import List

import altair as alt
import pandas as pd


DEFAULT_COLORS = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F"]


def grouped_bar_chart(
    df: pd.DataFrame,
    group_label: str,
    value_field: str,
    period_order: List[str],
) -> alt.Chart:
    subset = df[df["group"] == group_label]
    if subset.empty:
        return alt.Chart(pd.DataFrame({"node": [], value_field: []})).mark_bar()

    color_scale = alt.Scale(domain=period_order, range=DEFAULT_COLORS[: len(period_order)])

    chart = (
        alt.Chart(subset)
        .mark_bar()
        .encode(
            x=alt.X("node:N", sort=None, title=""),
            xOffset=alt.XOffset("period:N", sort=period_order),
            y=alt.Y(f"{value_field}:Q", title=value_field),
            color=alt.Color("period:N", scale=color_scale),
            tooltip=[
                alt.Tooltip("period:N"),
                alt.Tooltip("node:N"),
                alt.Tooltip(f"{value_field}:Q"),
                alt.Tooltip("tx_count:Q"),
            ],
        )
        .properties(height=320)
    )
    return chart
