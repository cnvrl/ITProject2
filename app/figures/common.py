from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import plotly.graph_objects as go


# Map colours shared by the track density and Welch t-test maps.
SEA_COLOUR = "#f6f9fc"
LAND_COLOUR = "#e6ecf1"
COASTLINE_COLOUR = "#6f8297"

LAND_FILE = Path(__file__).with_name("land_50m.json")


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
        font={"family": "Poppins, 'Segoe UI', system-ui, sans-serif"},
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


@lru_cache(maxsize=1)
def _land_outline() -> tuple[list, list]:
    """Load the Natural Earth land outline (x/y lists, polygons split by None)."""
    try:
        data = json.loads(LAND_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [], []

    return data.get("x", []), data.get("y", [])


@lru_cache(maxsize=1)
def _land_svg_path() -> str:
    xs, ys = _land_outline()
    parts: list[str] = []
    start = True

    for x, y in zip(xs, ys):
        if x is None or y is None:
            parts.append("Z")
            start = True
            continue

        parts.append(f"{'M' if start else 'L'}{x},{y}")
        start = False

    return " ".join(parts)


def coordinate_labels(
    lon_centers: np.ndarray,
    lat_centers: np.ndarray,
) -> list[list[str]]:
    """Hover labels such as "14°S, 121°E" for every cell of a lat x lon grid."""
    def lat_text(value: float) -> str:
        hemisphere = "S" if value < 0 else ("N" if value > 0 else "")
        return f"{abs(value):.0f}°{hemisphere}"

    return [
        [f"{lat_text(lat)}, {lon:.0f}°E" for lon in lon_centers]
        for lat in lat_centers
    ]


def add_land_and_coastline(
    figure: go.Figure,
    lon_range: tuple[float, float],
    lat_range: tuple[float, float],
    height: int | None,
) -> go.Figure:
    """
    Turn a cartesian figure into a simple lon/lat map.

    Plotly always draws heatmaps underneath scatter traces, whatever order the
    traces are added in. A filled land trace would therefore hide every heat
    cell over land. Land is added as a layout shape on the "below" layer
    instead, so heat cells cover it, and the coastline is added as a line
    trace that sits on top of the heat cells.
    """
    land_path = _land_svg_path()

    if land_path:
        figure.add_shape(
            type="path",
            path=land_path,
            xref="x",
            yref="y",
            fillcolor=LAND_COLOUR,
            line={"width": 0},
            layer="below",
        )

        xs, ys = _land_outline()
        figure.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": COASTLINE_COLOUR, "width": 0.9},
                hoverinfo="skip",
                showlegend=False,
                name="Coastline",
            )
        )

    # Ticks every 10 degrees, skipping any that sit on the map edge where
    # they would collide with the other axis's labels.
    lon_ticks = [
        value
        for value in range(int(np.ceil(lon_range[0] / 10) * 10), int(lon_range[1]) + 1, 10)
        if lon_range[0] + 2 <= value <= lon_range[1] - 2
    ]
    lat_ticks = [
        value
        for value in range(int(np.ceil(lat_range[0] / 10) * 10), int(lat_range[1]) + 1, 10)
        if lat_range[0] + 2 <= value <= lat_range[1] - 2
    ]

    figure.update_xaxes(
        range=list(lon_range),
        tickvals=lon_ticks,
        ticktext=[f"{value}°E" for value in lon_ticks],
        showgrid=True,
        gridcolor="#e3e9ef",
        zeroline=False,
        constrain="domain",
        fixedrange=True,
        title=None,
    )
    figure.update_yaxes(
        range=list(lat_range),
        tickvals=lat_ticks,
        ticktext=[
            f"{abs(value)}°{'S' if value < 0 else ('N' if value > 0 else '')}"
            for value in lat_ticks
        ],
        showgrid=True,
        gridcolor="#e3e9ef",
        zeroline=False,
        scaleanchor="x",
        scaleratio=1,
        constrain="domain",
        fixedrange=True,
        title=None,
    )
    figure.update_layout(
        template="plotly_white",
        autosize=True,
        plot_bgcolor=SEA_COLOUR,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Poppins, 'Segoe UI', system-ui, sans-serif", "size": 12, "color": "#5a6a85"},
    )

    # height=None lets the figure fill its dcc.Graph container, so CSS can size it.
    if height is not None:
        figure.update_layout(height=height)

    return figure
