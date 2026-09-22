from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SummaryMetrics:
    cyclone_count: int
    landfall_count: int
    landfall_rate: float
    average_wind: float
    peak_wind: float
    average_lifetime_hours: float
    median_lifetime_hours: float


def summary_metrics(
    tracks: pd.DataFrame,
) -> SummaryMetrics:
    if tracks.empty:
        return SummaryMetrics(
            cyclone_count=0,
            landfall_count=0,
            landfall_rate=0.0,
            average_wind=0.0,
            peak_wind=0.0,
            average_lifetime_hours=0.0,
            median_lifetime_hours=0.0,
        )

    count = len(tracks)
    landfalls = int(
        tracks["landfall"].fillna(False).sum()
    )

    wind = pd.to_numeric(
        tracks["max_wind_speed"],
        errors="coerce",
    ).fillna(0)

    lifetime = pd.to_numeric(
        tracks["lifetime_hours"],
        errors="coerce",
    ).fillna(0)

    return SummaryMetrics(
        cyclone_count=count,
        landfall_count=landfalls,
        landfall_rate=(
            landfalls / count * 100
            if count
            else 0.0
        ),
        average_wind=float(wind.mean()),
        peak_wind=float(wind.max()),
        average_lifetime_hours=float(
            lifetime.mean()
        ),
        median_lifetime_hours=float(
            lifetime.median()
        ),
    )


def frequency_by_model(
    tracks: pd.DataFrame,
) -> pd.DataFrame:
    if tracks.empty:
        return pd.DataFrame(
            columns=[
                "driving_model",
                "season",
                "cyclones",
            ]
        )

    return (
        tracks
        .dropna(
            subset=[
                "driving_model",
                "analysis_year",
                "track_id",
            ]
        )
        .groupby(
            [
                "driving_model",
                "analysis_year",
            ],
            as_index=False,
        )["track_id"]
        .nunique()
        .rename(
            columns={
                "analysis_year": "season",
                "track_id": "cyclones",
            }
        )
    )


def intensity_by_track(
    tracks: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "track_id",
        "driving_model",
        "max_wind_speed",
        "max_category",
    ]

    if tracks.empty:
        return pd.DataFrame(columns=columns)

    return (
        tracks[columns]
        .drop_duplicates(subset=["track_id"])
        .dropna(subset=["driving_model"])
        .copy()
    )


def longevity_by_track(
    tracks: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "track_id",
        "driving_model",
        "lifetime_hours",
    ]

    if tracks.empty:
        return pd.DataFrame(
            columns=columns + ["lifetime_days"]
        )

    result = (
        tracks[columns]
        .drop_duplicates(subset=["track_id"])
        .copy()
    )

    result["lifetime_hours"] = pd.to_numeric(
        result["lifetime_hours"],
        errors="coerce",
    )

    result = result[
        result["lifetime_hours"].ge(0)
    ].dropna(subset=["lifetime_hours"])

    result["lifetime_days"] = (
        result["lifetime_hours"] / 24.0
    )

    return result


def strongest_tracks(
    tracks: pd.DataFrame,
    limit: int = 12,
) -> pd.DataFrame:
    if tracks.empty:
        return tracks.copy()

    return tracks.sort_values(
        [
            "max_category",
            "max_wind_speed",
        ],
        ascending=False,
    ).head(limit).copy()


def comparison_summary(
    tracks: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "model",
        "cyclone_count",
        "mean_frequency_per_season",
        "mean_peak_wind_kmh",
        "maximum_wind_kmh",
        "mean_longevity_days",
        "landfall_count",
    ]

    if tracks.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict] = []

    for model, group in tracks.groupby(
        "driving_model"
    ):
        annual = (
            group.groupby("analysis_year")[
                "track_id"
            ]
            .nunique()
        )

        rows.append(
            {
                "model": model,
                "cyclone_count": int(
                    group["track_id"].nunique()
                ),
                "mean_frequency_per_season": (
                    float(annual.mean())
                    if not annual.empty
                    else 0.0
                ),
                "mean_peak_wind_kmh": float(
                    group["max_wind_speed"].mean()
                ),
                "maximum_wind_kmh": float(
                    group["max_wind_speed"].max()
                ),
                "mean_longevity_days": float(
                    group["lifetime_hours"].mean()
                    / 24
                ),
                "landfall_count": int(
                    group["landfall"].sum()
                ),
            }
        )

    return pd.DataFrame(rows, columns=columns)