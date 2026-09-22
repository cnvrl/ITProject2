from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from app.config import DATASET_TYPE_BY_FILE
from app.models.tc_record import TCRecord
from app.pipeline.ingest import Ingestor, infer_dataset_type


TRACK_COLUMNS = [
    "track_id",
    "name",
    "dataset",
    "driving_model",
    "raw_track_id",
    "season",
    "scenario",
    "region",
    "tracker",
    "year",
    "analysis_year",
    "max_category",
    "max_wind_speed",
    "lifetime_hours",
    "landfall",
    "genesis_lat",
    "genesis_lon",
    "last_lat",
    "last_lon",
    "genesis_date",
]

POINT_COLUMNS = [
    "track_id",
    "dataset",
    "driving_model",
    "tracker",
    "season",
    "scenario",
    "region",
    "step",
    "timestamp",
    "lat",
    "lon",
    "wind_speed",
    "pressure",
    "category",
]


@dataclass
class DashboardData:
    tracks: pd.DataFrame
    points: pd.DataFrame
    load_errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_loaded(self) -> bool:
        return not self.tracks.empty

    @property
    def year_min(self) -> int:
        years = pd.to_numeric(
            self.tracks.get(
                "analysis_year",
                pd.Series(dtype=float),
            ),
            errors="coerce",
        ).dropna()

        return int(years.min()) if not years.empty else 1980

    @property
    def year_max(self) -> int:
        years = pd.to_numeric(
            self.tracks.get(
                "analysis_year",
                pd.Series(dtype=float),
            ),
            errors="coerce",
        ).dropna()

        return int(years.max()) if not years.empty else 2025

    def unique_values(self, column: str) -> list[str]:
        if column not in self.tracks.columns:
            return []

        return sorted(
            self.tracks[column]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )


def _record_identifier(record: TCRecord) -> str:
    return (
        f"{record.dataset_id}:"
        f"{record.track_id}"
    )


def records_to_frames(
    records: Iterable[TCRecord],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    track_rows: list[dict[str, Any]] = []
    point_rows: list[dict[str, Any]] = []

    for record in records:
        identifier = _record_identifier(record)
        final_point = record.final_point

        raw_track_id = str(
            record.metadata.get("raw_track_id")
            or record.track_id
        )

        season = record.season or record.year
        analysis_year = season or record.year

        track_rows.append(
            {
                "track_id": identifier,
                "name": record.display_name,
                "dataset": record.dataset,
                "driving_model": record.source_model,
                "raw_track_id": raw_track_id,
                "season": season,
                "scenario": record.scenario,
                "region": record.region,
                "tracker": str(
                    record.tracker
                ).upper(),
                "year": record.year,
                "analysis_year": analysis_year,
                "max_category": int(
                    record.max_category or 0
                ),
                "max_wind_speed": float(
                    record.max_wind_speed or 0
                ),
                "lifetime_hours": float(
                    record.lifetime_hours or 0
                ),
                "landfall": bool(record.landfall),
                "genesis_lat": record.genesis_lat,
                "genesis_lon": record.genesis_lon,
                "last_lat": (
                    final_point.lat
                    if final_point
                    else record.genesis_lat
                ),
                "last_lon": (
                    final_point.lon
                    if final_point
                    else record.genesis_lon
                ),
                "genesis_date": (
                    record.genesis_time.date().isoformat()
                    if record.genesis_time
                    else None
                ),
            }
        )

        for index, point in enumerate(record.points):
            point_rows.append(
                {
                    "track_id": identifier,
                    "dataset": record.dataset,
                    "driving_model": record.source_model,
                    "tracker": str(
                        record.tracker
                    ).upper(),
                    "season": season,
                    "scenario": record.scenario,
                    "region": record.region,
                    "step": (
                        point.step
                        if point.step is not None
                        else index
                    ),
                    "timestamp": point.timestamp,
                    "lat": point.lat,
                    "lon": point.lon,
                    "wind_speed": (
                        point.wind_speed
                        if point.wind_speed is not None
                        else 0.0
                    ),
                    "pressure": point.pressure,
                    "category": (
                        point.category
                        if point.category is not None
                        else 0
                    ),
                }
            )

    tracks = pd.DataFrame(
        track_rows,
        columns=TRACK_COLUMNS,
    )

    points = pd.DataFrame(
        point_rows,
        columns=POINT_COLUMNS,
    )

    if not tracks.empty:
        numeric_columns = [
            "season",
            "year",
            "analysis_year",
            "max_category",
            "max_wind_speed",
            "lifetime_hours",
        ]

        for column in numeric_columns:
            tracks[column] = pd.to_numeric(
                tracks[column],
                errors="coerce",
            )

        tracks["max_category"] = (
            tracks["max_category"]
            .fillna(0)
            .clip(0, 5)
            .astype(int)
        )

    if not points.empty:
        for column in [
            "step",
            "lat",
            "lon",
            "wind_speed",
            "pressure",
            "category",
        ]:
            points[column] = pd.to_numeric(
                points[column],
                errors="coerce",
            )

    return tracks, points


def load_dashboard_data(
    data_dir: str | Path,
    *,
    strict_validation: bool = False,
) -> DashboardData:
    source_dir = Path(data_dir).expanduser().resolve()

    if not source_dir.exists():
        return DashboardData(
            tracks=pd.DataFrame(columns=TRACK_COLUMNS),
            points=pd.DataFrame(columns=POINT_COLUMNS),
            load_errors=[
                f"Data directory does not exist: {source_dir}"
            ],
        )

    ingestor = Ingestor(
        strict_validation=strict_validation
    )

    records: list[TCRecord] = []
    load_errors: list[str] = []
    file_metadata: list[dict[str, Any]] = []

    for path in sorted(source_dir.glob("*.csv")):
        dataset_type = DATASET_TYPE_BY_FILE.get(
            path.name.lower()
        ) or infer_dataset_type(path)

        if dataset_type is None:
            continue

        try:
            result = ingestor.ingest(
                path,
                dataset_type=dataset_type,
            )

            records.extend(result.records)
            file_metadata.append(result.metadata)

        except Exception as exc:  # noqa: BLE001
            load_errors.append(
                f"{path.name}: {exc}"
            )

    tracks, points = records_to_frames(records)

    return DashboardData(
        tracks=tracks,
        points=points,
        load_errors=load_errors,
        metadata={
            "files": file_metadata,
            "record_count": len(tracks),
            "point_count": len(points),
        },
    )