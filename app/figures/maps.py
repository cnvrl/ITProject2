from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from app.config import (
    CATEGORY_COLOURS,
    SETTINGS,
)
from app.figures.common import (
    add_land_and_coastline,
    coordinate_labels,
    empty_figure,
)


# Single-hue sequential blue, light (few tracks) to dark (many tracks).
DENSITY_SCALE = [
    [0.0, "#cde2fb"],
    [1 / 6, "#9ec5f4"],
    [2 / 6, "#6da7ec"],
    [3 / 6, "#3987e5"],
    [4 / 6, "#256abf"],
    [5 / 6, "#184f95"],
    [1.0, "#0d366b"],
]


def density_figure(
    density: np.ndarray,
    lon_centers: np.ndarray,
    lat_centers: np.ndarray,
    model: str,
    zmax: float | None = None,
    height: int = 500,
) -> go.Figure:
    """
    Track density map for one model: distinct tracks per season in each cell.

    Cells with no tracks are left empty so land and sea show through, and the
    coastline is drawn over the heat cells (see add_land_and_coastline).
    """
    if density.size == 0 or not np.any(density > 0):
        return empty_figure(
            f"No observations match {model}.",
            height=height,
        )

    z = np.where(density > 0, density, np.nan)
    upper = zmax if zmax and zmax > 0 else float(np.nanmax(z))
    half_cell = SETTINGS.density_cell_degrees / 2

    figure = go.Figure(
        go.Heatmap(
            x=lon_centers,
            y=lat_centers,
            z=z,
            zmin=0,
            zmax=upper,
            colorscale=DENSITY_SCALE,
            opacity=0.88,
            hoverongaps=False,
            text=coordinate_labels(lon_centers, lat_centers),
            hovertemplate=(
                "%{text}<br>"
                "<b>%{z:.2f}</b> tracks per season"
                "<extra></extra>"
            ),
            # Horizontal colour bar under the map, so the map gets the full width.
            colorbar={
                "title": {"text": "Tracks per season", "side": "top"},
                "orientation": "h",
                "thickness": 10,
                "len": 0.9,
                "x": 0.5,
                "xanchor": "center",
                "y": -0.06,
                "yanchor": "top",
                "tickfont": {"size": 11},
            },
        )
    )

    add_land_and_coastline(
        figure,
        lon_range=(
            float(lon_centers[0] - half_cell),
            float(lon_centers[-1] + half_cell),
        ),
        lat_range=(
            float(lat_centers[0] - half_cell),
            float(lat_centers[-1] + half_cell),
        ),
        # Sized by the tile's dcc.Graph (see density_card and .tile CSS).
        height=None,
    )

    figure.update_layout(
        margin={
            "l": 10,
            "r": 10,
            "t": 10,
            "b": 70,
        },
        showlegend=False,
        uirevision=f"density-{model}",
    )

    return figure


def _category_of(wind_kmh: float) -> int:
    for category, threshold in ((5, 200), (4, 160), (3, 118), (2, 89), (1, 63)):
        if wind_kmh >= threshold:
            return category
    return 0


def selected_track_figure(
    record: pd.Series,
    points: pd.DataFrame,
) -> go.Figure:
    """Map of one cyclone track, each point coloured by its category at that time."""
    ordered = points.dropna(subset=["lat", "lon"]).sort_values("step")

    if ordered.empty:
        return empty_figure(
            "Selected cyclone track is unavailable.",
            height=430,
        )

    lons = ordered["lon"].astype(float).to_numpy()
    lats = ordered["lat"].astype(float).to_numpy()
    winds = pd.to_numeric(ordered["wind_speed"], errors="coerce").fillna(0).to_numpy()
    pressures = pd.to_numeric(ordered["pressure"], errors="coerce")
    categories = [_category_of(float(w)) for w in winds]
    times = pd.to_datetime(ordered["timestamp"], errors="coerce", utc=True)
    time_text = [t.strftime("%d %b %Y %H:%M UTC") if pd.notna(t) else "" for t in times]
    pressure_text = [f"{p:.0f} hPa" if pd.notna(p) else "no pressure" for p in pressures]

    cyclone_name = (
        f"Cyclone {record['raw_track_id']} "
        f"({record['season']})"
    )

    figure = go.Figure()

    # Fit the view to the track, keeping at least 20 degrees across.
    centre_lon = (lons.min() + lons.max()) / 2
    centre_lat = (lats.min() + lats.max()) / 2
    span = max(lons.max() - lons.min(), (lats.max() - lats.min()) * 1.45, 20.0) * 1.2

    add_land_and_coastline(
        figure,
        lon_range=(centre_lon - span / 2, centre_lon + span / 2),
        lat_range=(centre_lat - span / 3, centre_lat + span / 3),
        height=430,
    )

    # Track line above the coastline, category markers above the line.
    figure.add_trace(
        go.Scatter(
            x=lons,
            y=lats,
            mode="lines",
            line={"color": "#5a6a85", "width": 1.5},
            hoverinfo="skip",
            showlegend=False,
        )
    )

    figure.add_trace(
        go.Scatter(
            x=lons,
            y=lats,
            mode="markers",
            marker={
                "size": 8,
                "color": [CATEGORY_COLOURS[c] for c in categories],
                "line": {"color": "#ffffff", "width": 1.5},
            },
            customdata=list(zip(winds, pressure_text, categories, time_text)),
            hovertemplate=(
                f"<b>{cyclone_name}</b><br>"
                "%{customdata[3]}<br>"
                "Wind: %{customdata[0]:.0f} km/h · %{customdata[1]}<br>"
                "Category %{customdata[2]}"
                "<extra></extra>"
            ),
            showlegend=False,
        )
    )

    peak = int(winds.argmax())

    figure.add_trace(
        go.Scatter(
            x=[record.get("genesis_lon", lons[0])],
            y=[record.get("genesis_lat", lats[0])],
            mode="markers",
            marker={
                "size": 13,
                "symbol": "circle-open",
                "color": "#2a3547",
                "line": {"width": 2},
            },
            hovertemplate="Genesis<extra></extra>",
            showlegend=False,
        )
    )

    figure.add_annotation(
        x=lons[0], y=lats[0], text="Genesis",
        showarrow=True, arrowhead=0, ax=-34, ay=-22,
        arrowcolor="#5a6a85", font={"size": 11, "color": "#2a3547"},
    )
    figure.add_annotation(
        x=lons[peak], y=lats[peak], text=f"Peak {winds[peak]:.0f} km/h",
        showarrow=True, arrowhead=0, ax=38, ay=26,
        arrowcolor="#5a6a85", font={"size": 11, "color": "#2a3547"},
    )

    figure.update_layout(
        margin={"l": 6, "r": 6, "t": 6, "b": 6},
        showlegend=False,
        font={"family": "Poppins, 'Segoe UI', system-ui, sans-serif", "size": 12, "color": "#5a6a85"},
    )

    return figure
