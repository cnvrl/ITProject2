from __future__ import annotations

import numpy as np
import plotly.graph_objects as go


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

    figure = go.Figure()

    figure.add_trace(
        go.Heatmap(
            z=mean_diff,
            x=lons,
            y=lats,
            colorscale="RdBu_r",
            zmid=0,
            colorbar={"title": "Δ Density / Season", "thickness": 14},
            hovertemplate=(
                "Lon: %{x:.1f}°E<br>"
                "Lat: %{y:.1f}°S<br>"
                "Δ Mean Density: %{z:.2f}<br>"
                "<extra></extra>"
            ),
        )
    )

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
        template="plotly_white",
        height=480,
        margin={"l": 50, "r": 20, "t": 30, "b": 50},
        xaxis_title="Longitude (°E)",
        yaxis_title="Latitude (°S)",
        legend={"orientation": "h", "x": 0.01, "y": 1.05},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    return figure