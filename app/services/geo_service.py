#GeoJSON conversion for cyclone-track API responses.



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


def to_feature_collection(
    frame: pd.DataFrame,
    *,
    limit: int = 250,
) -> dict[str, Any]:
    """Convert filtered cyclone points into a GeoJSON FeatureCollection."""
    if limit < 1 or limit > 2000:
        raise ValueError("limit must be between 1 and 2000.")

    if frame.empty:
        return {"type": "FeatureCollection", "count": 0, "features": []}

    working = frame.dropna(subset=["Lon", "Lat"]).copy()
    working["_time_sort"] = pd.to_datetime(
        working["Time"],
        errors="coerce",
        utc=True,
    )
    working = working.sort_values(TRACK_COLUMNS + ["_time_sort"])

    features: list[dict[str, Any]] = []

    for key, track in working.groupby(TRACK_COLUMNS, sort=False, dropna=False):
        if len(features) >= limit:
            break

        coordinates = [
            [float(lon), float(lat)]
            for lon, lat in zip(track["Lon"], track["Lat"])
        ]

        if len(coordinates) < 2:
            continue

        regional_model, driving_model, tracker, season, track_id = key
        time_values = track["_time_sort"].dropna()

        properties: dict[str, Any] = {
            "regional_model": str(regional_model),
            "driving_model": str(driving_model),
            "tracker": str(tracker),
            "season": int(season),
            "track_id": int(track_id),
            "point_count": len(coordinates),
            "maximum_wind": _safe_float(track["Wspd"].max()),
            "minimum_pressure": _safe_float(track["Pres"].min()),
            "start_time": (
                time_values.min().isoformat() if not time_values.empty else None
            ),
            "end_time": (
                time_values.max().isoformat() if not time_values.empty else None
            ),
        }

        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "count": len(features),
        "features": features,
    }


def _safe_float(value: Any) -> float | None:
    return None if pd.isna(value) else float(value)
