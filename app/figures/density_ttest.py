from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from app.figures.common import add_land_and_coastline, coordinate_labels


def welch_pvalue_map_figure(
    welch_res: dict[str, np.ndarray],
    alpha: float = 0.05,
) -> go.Figure:
    """Render spatial density difference heatmap with significance overlays."""
    p_values = welch_res["p_values"]
    mean_diff = welch_res["mean_diff"]
    lons = welch_res["lon_centers"]
    lats = welch_res["lat_centers"]

    if np.all(np.isnan(p_values)):
        figure = go.Figure()
        figure.add_annotation(
            text="Select both historical (<= 2014) and future (> 2014) seasons to render Welch's t-test grid.",
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font={"size": 14, "color": "#64748b"},
        )
        figure.update_layout(
            template="plotly_white",
            height=480,
            xaxis={"visible": False},
            yaxis={"visible": False},
        )
        return figure

    significant_mask = p_values < alpha

    # Cells with no tracks in either period have no test result; leave them
    # empty so the land and sea underneath stay visible.
    no_data = np.isnan(p_values) & (mean_diff == 0)
    z = np.where(no_data, np.nan, mean_diff)

    figure = go.Figure()

    figure.add_trace(
        go.Heatmap(
            z=z,
            x=lons,
            y=lats,
            colorscale="RdBu_r",
            zmid=0,
            hoverongaps=False,
            text=coordinate_labels(lons, lats),
            colorbar={"title": "Δ Density / Season", "thickness": 14},
            hovertemplate=(
                "%{text}<br>"
                "Δ Mean Density: %{z:.2f}<br>"
                "<extra></extra>"
            ),
        )
    )

    half_lon = float(lons[1] - lons[0]) / 2 if len(lons) > 1 else 0.5
    half_lat = float(lats[1] - lats[0]) / 2 if len(lats) > 1 else 0.5

    add_land_and_coastline(
        figure,
        lon_range=(float(lons[0] - half_lon), float(lons[-1] + half_lon)),
        lat_range=(float(lats[0] - half_lat), float(lats[-1] + half_lat)),
        height=480,
    )

    # Added after the coastline so the significance markers sit on top.
    sig_lons, sig_lats = np.meshgrid(lons, lats)
    figure.add_trace(
        go.Scatter(
            x=sig_lons[significant_mask],
            y=sig_lats[significant_mask],
            mode="markers",
            marker={"size": 5, "color": "#0f172a", "symbol": "x"},
            name=f"p < {alpha} (Significant)",
            hovertemplate="Significant change (p < 0.05)<extra></extra>",
        )
    )

    figure.update_layout(
        margin={"l": 50, "r": 20, "t": 40, "b": 40},
        showlegend=True,
        legend={"orientation": "h", "x": 0, "xanchor": "left", "y": 1.01, "yanchor": "bottom"},
    )

    return figure
