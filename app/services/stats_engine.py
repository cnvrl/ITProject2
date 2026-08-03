"""Statistical calculations for the TC-Explorer backend."""

from __future__ import annotations

from typing import Any

import pandas as pd


TRACK_COLUMNS = [
    "RegionalModel",
    "Model",
    "Tracker",
    "Season",
    "TrackID",
]


def calculate_statistics(
    frame: pd.DataFrame,
    metric: str,
) -> dict[str, Any]:
    """Calculate one supported statistical response."""
    metric = metric.casefold()

    if metric == "summary":
        return _summary(frame)

    if metric == "frequency":
        return _frequency(frame)

    if metric == "intensity":
        return _intensity(frame)

    if metric in {"lifetime", "translation_speed"}:
        raise NotImplementedError(
            f"{metric} requires Member 2 to confirm and normalise the Time "
            "field before the backend calculates it."
        )

    raise ValueError(
        "metric must be summary, frequency, intensity, lifetime, "
        "or translation_speed."
    )


def _summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {
            "metric": "summary",
            "row_count": 0,
            "track_count": 0,
            "season_min": None,
            "season_max": None,
            "maximum_wind": None,
            "minimum_pressure": None,
        }

    tracks = frame[TRACK_COLUMNS].drop_duplicates()

    return {
        "metric": "summary",
        "row_count": int(len(frame)),
        "track_count": int(len(tracks)),
        "season_min": int(frame["Season"].min()),
        "season_max": int(frame["Season"].max()),
        "maximum_wind": _safe_float(frame["Wspd"].max()),
        "minimum_pressure": _safe_float(frame["Pres"].min()),
    }


def _frequency(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"metric": "frequency", "results": []}

    result = (
        frame.groupby(
            ["RegionalModel", "Model", "Tracker", "Season"],
            dropna=False,
        )["TrackID"]
        .nunique()
        .reset_index(name="cyclone_count")
        .sort_values(["Model", "Season"])
    )

    result = result.rename(
        columns={
            "RegionalModel": "regional_model",
            "Model": "driving_model",
            "Tracker": "tracker",
            "Season": "season",
        }
    )

    return {
        "metric": "frequency",
        "results": result.to_dict(orient="records"),
    }


def _intensity(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"metric": "intensity", "results": []}

    per_track = (
        frame.groupby(TRACK_COLUMNS, dropna=False)
        .agg(
            maximum_wind=("Wspd", "max"),
            minimum_pressure=("Pres", "min"),
        )
        .reset_index()
    )

    result = (
        per_track.groupby(
            ["RegionalModel", "Model", "Tracker"],
            dropna=False,
        )
        .agg(
            track_count=("TrackID", "count"),
            mean_track_maximum_wind=("maximum_wind", "mean"),
            overall_maximum_wind=("maximum_wind", "max"),
            mean_track_minimum_pressure=("minimum_pressure", "mean"),
            overall_minimum_pressure=("minimum_pressure", "min"),
        )
        .reset_index()
        .rename(
            columns={
                "RegionalModel": "regional_model",
                "Model": "driving_model",
                "Tracker": "tracker",
            }
        )
    )

    numeric_columns = [
        "mean_track_maximum_wind",
        "overall_maximum_wind",
        "mean_track_minimum_pressure",
        "overall_minimum_pressure",
    ]
    result[numeric_columns] = result[numeric_columns].round(3)

    return {
        "metric": "intensity",
        "results": result.to_dict(orient="records"),
    }


def _safe_float(value: Any) -> float | None:
    return None if pd.isna(value) else float(value)
