from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from app.models.tc_record import TCRecord


@dataclass(frozen=True)
class DashboardSummaryMetrics:
    cyclone_count: int
    landfall_count: int
    landfall_rate: float
    average_wind: float
    peak_wind: float
    average_lifetime_hours: float
    median_lifetime_hours: float


def summary_metrics(tracks: pd.DataFrame) -> DashboardSummaryMetrics:
    if tracks.empty:
        return DashboardSummaryMetrics(0, 0, 0.0, 0.0, 0.0, 0.0, 0.0)

    total_count = len(tracks)
    landfall_count = int(tracks["landfall"].sum())
    landfall_rate = (landfall_count / total_count * 100.0) if total_count > 0 else 0.0

    avg_wind = float(tracks["max_wind_speed"].mean())
    peak_wind = float(tracks["max_wind_speed"].max())
    avg_lifetime = float(tracks["lifetime_hours"].mean())
    med_lifetime = float(tracks["lifetime_hours"].median())

    return DashboardSummaryMetrics(
        cyclone_count=total_count,
        landfall_count=landfall_count,
        landfall_rate=landfall_rate,
        average_wind=avg_wind,
        peak_wind=peak_wind,
        average_lifetime_hours=avg_lifetime,
        median_lifetime_hours=med_lifetime,
    )


def frequency_by_model(tracks: pd.DataFrame) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(columns=["season", "driving_model", "cyclones"])

    grouped = (
        tracks.groupby(["season", "driving_model"])
        .size()
        .reset_index(name="cyclones")
    )
    return grouped


def intensity_by_track(tracks: pd.DataFrame) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(columns=["driving_model", "max_wind_speed"])
    return tracks[["driving_model", "max_wind_speed"]].copy()


def longevity_by_track(tracks: pd.DataFrame) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(columns=["driving_model", "lifetime_days"])

    df = tracks[["driving_model", "lifetime_hours"]].copy()
    df["lifetime_days"] = df["lifetime_hours"] / 24.0
    return df


def strongest_tracks(tracks: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame()
    return tracks.sort_values("max_wind_speed", ascending=False).head(limit)


def comparison_summary(tracks: pd.DataFrame) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame()

    summary = tracks.groupby("driving_model").agg(
        total_cyclones=("track_id", "count"),
        avg_wind_kmh=("max_wind_speed", "mean"),
        max_wind_kmh=("max_wind_speed", "max"),
        avg_duration_hours=("lifetime_hours", "mean"),
        landfalls=("landfall", "sum"),
    ).reset_index()

    # Alias 'model' to 'driving_model' for compatibility with report generators
    summary["model"] = summary["driving_model"]

    return summary