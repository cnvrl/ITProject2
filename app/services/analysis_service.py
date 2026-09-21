from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

MAP_EXTENT = (100.0, 180.0, -60.0, 0.0)
LON_BINS = 40
LAT_BINS = 30
LONGEVITY_DISPLAY_LIMIT_DAYS = 60
PLOT_COLORS = ["#1769aa", "#d97706", "#0f766e", "#7c3aed", "#be123c", "#4d7c0f", "#0369a1", "#a16207"]


def empty_figure(message: str, height: int = 380) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, showarrow=False, font={"size": 15, "color": "#64748b"})
    fig.update_layout(
        template="plotly_white", height=height, xaxis={"visible": False}, yaxis={"visible": False},
        margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def calculate_frequency(tracks: pd.DataFrame) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(columns=["analysis_label", "season", "frequency"])
    return (
        tracks.drop_duplicates("track_id")
        .groupby(["analysis_label", "season"], as_index=False)
        .size()
        .rename(columns={"size": "frequency"})
        .sort_values(["analysis_label", "season"])
    )


def calculate_intensity(tracks: pd.DataFrame) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(columns=["analysis_label", "track_id", "max_wind_speed"])
    return tracks[["analysis_label", "track_id", "max_wind_speed"]].drop_duplicates("track_id")


def calculate_longevity(tracks: pd.DataFrame) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(columns=["analysis_label", "track_id", "duration_days"])
    result = tracks[["analysis_label", "track_id", "lifetime_hours"]].drop_duplicates("track_id").copy()
    result["duration_days"] = result["lifetime_hours"] / 24.0
    return result


def density_grid(points: pd.DataFrame, lon_bins: int = LON_BINS, lat_bins: int = LAT_BINS):
    west, east, south, north = MAP_EXTENT
    clean = points[
        points["lon"].between(west, east) & points["lat"].between(south, north)
    ]
    lon_edges = np.linspace(west, east, lon_bins + 1)
    lat_edges = np.linspace(south, north, lat_bins + 1)
    density, _, _ = np.histogram2d(clean["lat"], clean["lon"], bins=[lat_edges, lon_edges])
    return density, lon_edges, lat_edges


def build_frequency_figure(tracks: pd.DataFrame) -> go.Figure:
    frequency = calculate_frequency(tracks)
    if frequency.empty:
        return empty_figure("No frequency data matches the filters")
    fig = go.Figure()
    for index, (label, frame) in enumerate(frequency.groupby("analysis_label", sort=True)):
        frame = frame.sort_values("season").copy()
        frame["running_mean"] = frame["frequency"].rolling(5, center=True, min_periods=1).mean()
        color = PLOT_COLORS[index % len(PLOT_COLORS)]
        fig.add_trace(go.Scatter(
            x=frame["season"], y=frame["frequency"], mode="lines+markers", name=f"{label} — annual",
            line={"width": 1, "color": color}, marker={"size": 4}, opacity=0.35,
            hovertemplate=f"<b>{label}</b><br>Season %{{x}}<br>%{{y}} tracks<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=frame["season"], y=frame["running_mean"], mode="lines", name=f"{label} — 5-season mean",
            line={"width": 3, "color": color},
            hovertemplate=f"<b>{label}</b><br>Season %{{x}}<br>5-season mean %{{y:.1f}}<extra></extra>",
        ))
    fig.update_layout(
        template="plotly_white", height=430, margin=dict(l=55, r=20, t=25, b=55),
        xaxis_title="Season", yaxis_title="Unique cyclone tracks", hovermode="x unified",
        legend={"orientation": "h", "y": -0.24, "x": 0}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _box_figure(tracks: pd.DataFrame, value_column: str, y_title: str, limit: float | None = None) -> go.Figure:
    if tracks.empty:
        return empty_figure(f"No {y_title.lower()} data matches the filters")
    fig = go.Figure()
    for index, (label, frame) in enumerate(tracks.groupby("analysis_label", sort=True)):
        values = frame[value_column].dropna()
        if values.empty:
            continue
        fig.add_trace(go.Box(
            y=values, name=label, boxmean=True, boxpoints="outliers", jitter=0.25,
            marker={"color": PLOT_COLORS[index % len(PLOT_COLORS)], "size": 4},
            line={"color": PLOT_COLORS[index % len(PLOT_COLORS)]},
            hovertemplate=f"<b>{label}</b><br>%{{y:.2f}}<extra></extra>",
        ))
    if not fig.data:
        return empty_figure(f"No {y_title.lower()} data matches the filters")
    fig.update_layout(
        template="plotly_white", height=430, margin=dict(l=60, r=20, t=25, b=100),
        yaxis_title=y_title, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(tickangle=-15)
    if limit is not None:
        fig.update_yaxes(range=[0, limit])
        fig.add_annotation(
            text=f"Display capped at {limit:g} days; all tracks remain in statistics and downloads.",
            x=1, y=1.08, xref="paper", yref="paper", xanchor="right", showarrow=False,
            font={"size": 11, "color": "#64748b"},
        )
    return fig


def build_intensity_figure(tracks: pd.DataFrame) -> go.Figure:
    return _box_figure(calculate_intensity(tracks), "max_wind_speed", "Maximum wind per cyclone (km/h)")


def build_longevity_figure(tracks: pd.DataFrame) -> go.Figure:
    return _box_figure(calculate_longevity(tracks), "duration_days", "Duration (days)", LONGEVITY_DISPLAY_LIMIT_DAYS)


def build_heatmap_figure(points: pd.DataFrame, labels: Iterable[str]) -> go.Figure:
    label_list = [label for label in labels if label in set(points.get("analysis_label", []))]
    if not label_list or points.empty:
        return empty_figure("No track points match the filters", height=520)
    cols = 2 if len(label_list) > 1 else 1
    rows = int(np.ceil(len(label_list) / cols))
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=label_list, horizontal_spacing=0.08, vertical_spacing=0.13)
    grids = []
    global_max = 0.0
    for label in label_list:
        density, lon_edges, lat_edges = density_grid(points[points["analysis_label"] == label])
        global_max = max(global_max, float(density.max()))
        grids.append((density, lon_edges, lat_edges))
    for index, (label, grid) in enumerate(zip(label_list, grids)):
        density, lon_edges, lat_edges = grid
        row, col = divmod(index, cols)
        fig.add_trace(go.Heatmap(
            z=np.where(density > 0, density, np.nan),
            x=(lon_edges[:-1] + lon_edges[1:]) / 2,
            y=(lat_edges[:-1] + lat_edges[1:]) / 2,
            colorscale="YlOrRd", zmin=0, zmax=global_max or None,
            colorbar={"title": "Points", "len": 0.78} if index == 0 else None,
            showscale=index == 0,
            hovertemplate=f"<b>{label}</b><br>Lon %{{x:.1f}}°<br>Lat %{{y:.1f}}°<br>%{{z:.0f}} points<extra></extra>",
        ), row=row + 1, col=col + 1)
        fig.update_xaxes(title_text="Longitude", range=[MAP_EXTENT[0], MAP_EXTENT[1]], row=row + 1, col=col + 1)
        fig.update_yaxes(title_text="Latitude", range=[MAP_EXTENT[2], MAP_EXTENT[3]], row=row + 1, col=col + 1)
    fig.update_layout(
        template="plotly_white", height=max(500, 390 * rows), margin=dict(l=55, r=45, t=55, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _trend(x: pd.Series, y: pd.Series) -> float:
    if len(x) < 2 or x.nunique() < 2:
        return np.nan
    return float(np.polyfit(x.astype(float), y.astype(float), 1)[0])


def build_summary(tracks: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    if tracks.empty:
        return pd.DataFrame()
    for label, frame in tracks.groupby("analysis_label", sort=True):
        frame = frame.drop_duplicates("track_id")
        frequency = calculate_frequency(frame)
        intensity = frame["max_wind_speed"].dropna()
        duration = (frame["lifetime_hours"] / 24.0).dropna()
        label_points = points[points["analysis_label"] == label]
        density, lon_edges, lat_edges = density_grid(label_points)
        if density.size and density.max() > 0:
            row_index, col_index = np.unravel_index(np.argmax(density), density.shape)
            hot_lon = float((lon_edges[col_index] + lon_edges[col_index + 1]) / 2)
            hot_lat = float((lat_edges[row_index] + lat_edges[row_index + 1]) / 2)
            hot_count = float(density[row_index, col_index])
            lon_centres = (lon_edges[:-1] + lon_edges[1:]) / 2
            lat_centres = (lat_edges[:-1] + lat_edges[1:]) / 2
            lon_grid, lat_grid = np.meshgrid(lon_centres, lat_centres)
            total = density.sum()
            centre_lon = float((density * lon_grid).sum() / total)
            centre_lat = float((density * lat_grid).sum() / total)
        else:
            hot_lon = hot_lat = centre_lon = centre_lat = np.nan
            hot_count = 0.0
        rows.append({
            "Combination": label,
            "Rows": int(len(label_points)),
            "CycloneTracks": int(len(frame)),
            "SeasonMin": int(frame["season"].min()),
            "SeasonMax": int(frame["season"].max()),
            "MeanFrequency": float(frequency["frequency"].mean()),
            "MedianFrequency": float(frequency["frequency"].median()),
            "MaxFrequency": float(frequency["frequency"].max()),
            "FrequencyTrendPerSeason": _trend(frequency["season"], frequency["frequency"]),
            "MeanMaxWind": float(intensity.mean()),
            "MedianMaxWind": float(intensity.median()),
            "P90MaxWind": float(intensity.quantile(0.90)),
            "StrongestTrackWind": float(intensity.max()),
            "MeanDurationDays": float(duration.mean()),
            "MedianDurationDays": float(duration.median()),
            "P90DurationDays": float(duration.quantile(0.90)),
            "LongestDurationDays": float(duration.max()),
            "HotspotLon": hot_lon,
            "HotspotLat": hot_lat,
            "HotspotCount": hot_count,
            "DensityCentreLon": centre_lon,
            "DensityCentreLat": centre_lat,
        })
    return pd.DataFrame(rows)
