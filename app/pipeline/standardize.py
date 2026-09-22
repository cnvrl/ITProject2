from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Iterable, Optional

from app.config import SETTINGS
from app.models.tc_record import (
    TCRecord,
    TrackPoint,
    coerce_datetime,
)


def normalise_text(
    value: object,
    default: str = "unknown",
) -> str:
    text = str(
        value if value is not None else ""
    ).strip()

    return text if text else default


def normalise_longitude(longitude: float) -> float:
    """Normalise longitude to the range -180 to 180."""

    value = float(longitude)

    while value > 180:
        value -= 360

    while value < -180:
        value += 360

    return value


def category_from_wind_kmh(
    wind_speed: Optional[float],
) -> int:
    """Assign an Australian tropical cyclone category from wind in km/h."""

    if wind_speed is None:
        return 0

    wind = float(wind_speed)

    if wind >= 200:
        return 5
    if wind >= 160:
        return 4
    if wind >= 118:
        return 3
    if wind >= 89:
        return 2
    if wind >= 63:
        return 1

    return 0


def resolve_scenario(
    driving_model: object,
    season: object,
    source_scenario: object = None,
) -> str:
    """
    Correct historical/future scenario labels.

    ERA5 is treated as historical/reanalysis data. Seasons up to and
    including the configured historical end year are historical. Seasons
    from the configured future start year onward are future scenario
    records.
    """

    model = normalise_text(
        driving_model,
        default="",
    ).upper()

    try:
        year = int(float(season))
    except (TypeError, ValueError):
        source = normalise_text(
            source_scenario,
        ).lower()

        return source

    if model == "ERA5":
        return "historical"

    if year <= SETTINGS.historical_end_year:
        return "historical"

    return "future"


def standardize_point(
    point: TrackPoint,
    index: int,
) -> TrackPoint:
    standard_point = deepcopy(point)

    standard_point.lat = float(standard_point.lat)
    standard_point.lon = normalise_longitude(
        standard_point.lon
    )

    standard_point.step = (
        int(standard_point.step)
        if standard_point.step is not None
        else index
    )

    if standard_point.timestamp is not None:
        standard_point.timestamp = coerce_datetime(
            standard_point.timestamp
        )

    if standard_point.wind_speed is not None:
        standard_point.wind_speed = max(
            0.0,
            float(standard_point.wind_speed),
        )

    if standard_point.pressure is not None:
        standard_point.pressure = float(
            standard_point.pressure
        )

    if standard_point.category is None:
        standard_point.category = category_from_wind_kmh(
            standard_point.wind_speed
        )
    else:
        standard_point.category = max(
            0,
            min(5, int(standard_point.category)),
        )

    return standard_point


def _point_sort_key(
    point: TrackPoint,
) -> tuple[int, datetime, int]:
    if point.timestamp is not None:
        return (
            0,
            point.timestamp,
            int(point.step or 0),
        )

    return (
        1,
        datetime.max,
        int(point.step or 0),
    )


def standardize_record(
    record: TCRecord,
) -> TCRecord:
    """Return a normalised copy of one cyclone record."""

    standard_record = deepcopy(record)

    standard_record.dataset_id = normalise_text(
        standard_record.dataset_id
    )

    standard_record.track_id = normalise_text(
        standard_record.track_id
    )

    standard_record.model = normalise_text(
        standard_record.model
    ).upper()

    standard_record.driving_model = normalise_text(
        standard_record.source_model
    )

    standard_record.tracker = normalise_text(
        standard_record.tracker
    ).upper()

    standard_record.region = normalise_text(
        standard_record.region,
        default=SETTINGS.default_region,
    )

    if standard_record.season is None:
        metadata_season = standard_record.metadata.get(
            "season"
        )

        if metadata_season is not None:
            try:
                standard_record.season = int(
                    float(metadata_season)
                )
            except (TypeError, ValueError):
                standard_record.season = None

    if standard_record.year is not None:
        try:
            standard_record.year = int(
                float(standard_record.year)
            )
        except (TypeError, ValueError):
            standard_record.year = None

    if standard_record.season is None:
        standard_record.season = standard_record.year

    if standard_record.year is None:
        standard_record.year = standard_record.season

    standard_record.scenario = resolve_scenario(
        standard_record.source_model,
        standard_record.season,
        standard_record.scenario,
    )

    standard_record.points = [
        standardize_point(point, index)
        for index, point in enumerate(
            standard_record.points
        )
    ]

    standard_record.points.sort(key=_point_sort_key)

    for index, point in enumerate(standard_record.points):
        point.step = index

    standard_record.refresh_derived_fields()

    standard_record.metadata = dict(
        standard_record.metadata
    )

    standard_record.metadata.update(
        {
            "source_model_value": standard_record.source_model,
            "raw_track_id": (
                standard_record.metadata.get("raw_track_id")
                or standard_record.track_id
            ),
            "season": standard_record.season,
            "standardized": True,
        }
    )

    return standard_record


def standardize_records(
    records: Iterable[TCRecord],
) -> list[TCRecord]:
    """Standardise a collection of cyclone records."""

    return [
        standardize_record(record)
        for record in records
    ]