from __future__ import annotations

import plotly.graph_objects as go


def empty_figure(
    message: str,
    height: int = 360,
) -> go.Figure:
    figure = go.Figure()

    figure.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={
            "size": 15,
            "color": "#64748b",
        },
    )

    figure.update_layout(
        template="plotly_white",
        height=height,
        autosize=True,
        xaxis={"visible": False},
        yaxis={"visible": False},
        margin={
            "l": 20,
            "r": 20,
            "t": 20,
            "b": 20,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return figure