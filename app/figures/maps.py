from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.config import (
    CATEGORY_COLOURS,
    SETTINGS,
)
from app.figures.common import empty_figure


DENSITY_SCALE = [
    [0.0, "rgba(23,105,170,0.00)"],
    [0.20, "#8ecae6"],
    [0.50, "#219ebc"],
    [0.75, "#ffb703"],
    [1.0, "#d62828"],
]


def density_figure(
    points: pd.DataFrame,
    model: str,
) -> go.Figure:
    if points.empty:
        return empty_figure(
            f"No observations match {model}.",
            height=500,
        )

    mapped = points[
        points["lat"].between(
            SETTINGS.heatmap_min_latitude,
            SETTINGS.heatmap_max_latitude,
        )
        & points["lon"].between(
            SETTINGS.heatmap_min_longitude,
            SETTINGS.heatmap_max_longitude,
        )
    ].dropna(
        subset=["lat", "lon"]
    ).copy()

    if mapped.empty:
        return empty_figure(
            f"No Australian-region points match {model}.",
            height=500,
        )

    if len(mapped) > SETTINGS.heatmap_max_points:
        mapped = mapped.sample(
            SETTINGS.heatmap_max_points,
            random_state=42,
        )

    figure = px.density_map(
        mapped,
        lat="lat",
        lon="lon",
        radius=9,
        center={
            "lat": -24.5,
            "lon": 134.5,
        },
        zoom=2.65,
        map_style="carto-positron",
        color_continuous_scale=DENSITY_SCALE,
    )

    figure.update_layout(
        height=500,
        autosize=True,
        margin={
            "l": 0,
            "r": 0,
            "t": 0,
            "b": 0,
        },
        coloraxis_colorbar={
            "title": "Density",
            "thickness": 14,
        },
        uirevision=f"density-{model}",
    )

    return figure


def selected_track_figure(
    record: pd.Series,
    points: pd.DataFrame,
) -> go.Figure:
    if points.empty:
        return empty_figure(
            "Selected cyclone track is unavailable.",
            height=430,
        )

    category = int(
        max(
            0,
            min(
                5,
                record.get("max_category", 0),
            ),
        )
    )

    colour = CATEGORY_COLOURS[category]

    cyclone_name = (
        f"Cyclone {record['raw_track_id']} "
        f"({record['season']})"
    )

    ordered = points.sort_values("step")
    figure = go.Figure()

    figure.add_trace(
        go.Scattergeo(
            lon=ordered["lon"],
            lat=ordered["lat"],
            mode="lines+markers",
            line={
                "width": 3,
                "color": colour,
            },
            marker={
                "size": 5,
                "color": colour,
            },
            customdata=ordered[
                ["wind_speed", "category"]
            ],
            name=cyclone_name,
            hovertemplate=(
                f"<b>{cyclone_name}</b>"
                "<br>Wind: %{customdata[0]:.0f} km/h"
                "<br>Category: %{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scattergeo(
            lon=[record["genesis_lon"]],
            lat=[record["genesis_lat"]],
            mode="markers",
            marker={
                "size": 11,
                "color": "#0f172a",
                "line": {
                    "width": 2,
                    "color": "white",
                },
            },
            name="Genesis",
        )
    )

    figure.update_geos(
        projection_type="mercator",
        lonaxis_range=[
            SETTINGS.heatmap_min_longitude,
            SETTINGS.heatmap_max_longitude,
        ],
        lataxis_range=[
            SETTINGS.heatmap_min_latitude,
            SETTINGS.heatmap_max_latitude,
        ],
        showland=True,
        landcolor="#e9eef3",
        showocean=True,
        oceancolor="#eaf7fb",
        showcoastlines=True,
        coastlinecolor="#94a3b8",
        showcountries=True,
        countrycolor="#cbd5e1",
        resolution=50,
    )

    figure.update_layout(
        height=430,
        margin={
            "l": 0,
            "r": 0,
            "t": 0,
            "b": 0,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        legend={
            "orientation": "h",
            "x": 0.01,
            "y": 0.01,
        },
    )

    return figure