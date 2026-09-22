from __future__ import annotations

import re
from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import pandas as pd

from app.models.tc_record import TCRecord, TrackPoint


class LoaderError(ValueError):
    """Raised when a dataset cannot be converted into cyclone records."""


@dataclass
class LoaderResult:
    """Structured result returned by a dataset loader."""

    records: list[TCRecord]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": self.records,
            "metadata": dict(self.metadata),
        }

    def get(
        self,
        key: str,
        default: object = None,
    ) -> object:
        return self.to_dict().get(key, default)

    def __getitem__(self, key: str) -> object:
        return self.to_dict()[key]


def normalise_column_name(value: object) -> str:
    """
    Convert a source column name into a predictable snake-case name.

    Examples:
        Track ID -> track_id
        WindSpeed -> wind_speed
        LATITUDE -> latitude
    """

    text = str(value).strip()

    text = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1_\2",
        text,
    )

    text = re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        text,
    )

    return text.strip("_").lower()


def safe_text(
    value: object,
    default: str = "",
) -> str:
    if value is None or pd.isna(value):
        return default

    text = str(value).strip()

    return text if text else default


def safe_float(value: object) -> Optional[float]:
    if value is None or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_int(value: object) -> Optional[int]:
    if value is None or pd.isna(value):
        return None

    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def safe_bool(value: object) -> bool:
    if value is None or pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "landfall",
        "landfalling",
    }


def safe_datetime(value: object):
    if value is None or pd.isna(value):
        return None

    timestamp = pd.to_datetime(
        value,
        errors="coerce",
        utc=True,
    )

    if pd.isna(timestamp):
        return None

    return timestamp.to_pydatetime()


def source_scenario_from_filename(path: Path) -> str:
    """Read a scenario hint from the source filename."""

    filename = path.stem.lower()

    patterns = (
        r"ssp\d+",
        r"rcp\d+",
        r"historical",
        r"future",
    )

    for pattern in patterns:
        match = re.search(pattern, filename)

        if match:
            return match.group(0)

    return "unknown"


class BaseCSVTrackLoader(ABC):
    """
    Shared loader for BARPA and CCAM cyclone-track CSV files.

    Subclasses only define:
        dataset_type
        dataset_label
        filename_tokens

    This class handles:
        - column-name normalisation;
        - source-column discovery;
        - numeric and timestamp conversion;
        - wind-unit conversion;
        - grouping point rows into cyclone records;
        - metadata preservation;
        - creation of TCRecord and TrackPoint objects.
    """

    dataset_type: str = ""
    dataset_label: str = ""
    filename_tokens: tuple[str, ...] = ()

    column_aliases: Mapping[str, tuple[str, ...]] = {
        "track_id": (
            "track_id",
            "trackid",
            "track",
            "tc_id",
            "tcid",
            "cyclone_id",
            "cycloneid",
            "storm_id",
            "stormid",
            "event_id",
        ),
        "driving_model": (
            "driving_model",
            "source_model",
            "source_model_value",
            "climate_model",
            "global_model",
            "gcm",
            "model",
        ),
        "tracker": (
            "tracker",
            "tracking_algorithm",
            "track_algorithm",
            "tracker_name",
            "algorithm",
        ),
        "season": (
            "season",
            "season_year",
            "storm_season",
            "cyclone_season",
            "year",
        ),
        "year": (
            "year",
            "calendar_year",
        ),
        "segment": (
            "segment",
            "segment_id",
            "segment_number",
            "track_segment",
        ),
        "timestamp": (
            "timestamp",
            "datetime",
            "date_time",
            "date",
            "time",
            "valid_time",
            "observation_time",
            "iso_time",
        ),
        "step": (
            "step",
            "time_step",
            "timestep",
            "track_step",
            "point",
            "point_index",
            "index",
        ),
        "latitude": (
            "latitude",
            "lat",
            "y",
        ),
        "longitude": (
            "longitude",
            "lon",
            "long",
            "lng",
            "x",
        ),
        "wind_speed": (
            "wind_speed",
            "windspeed",
            "wind",
            "vmax",
            "max_wind",
            "maximum_wind",
            "max_wind_speed",
            "wind_kmh",
            "wind_speed_kmh",
            "wind_ms",
            "wind_speed_ms",
            "wind_mps",
            "wind_speed_mps",
            "wind_kt",
            "wind_speed_kt",
            "wind_knots",
        ),
        "pressure": (
            "pressure",
            "central_pressure",
            "minimum_pressure",
            "min_pressure",
            "mslp",
            "slp",
            "pressure_hpa",
            "pressure_pa",
        ),
        "category": (
            "category",
            "intensity_category",
            "cyclone_category",
            "australian_category",
            "max_category",
        ),
        "scenario": (
            "scenario",
            "experiment",
            "experiment_id",
            "climate_scenario",
        ),
        "region": (
            "region",
            "basin",
            "domain",
            "area",
        ),
        "landfall": (
            "landfall",
            "made_landfall",
            "is_landfall",
            "landfall_flag",
        ),
    }

    required_fields = (
        "track_id",
        "latitude",
        "longitude",
    )

    def __init__(
        self,
        *,
        default_region: str = "Australia",
        default_wind_unit: str = "auto",
    ) -> None:
        self.default_region = default_region
        self.default_wind_unit = default_wind_unit

    def supports(
        self,
        path: Path,
        dataset_type: Optional[str] = None,
    ) -> bool:
        """
        Return whether this loader supports the requested file.

        Explicit dataset type takes precedence over filename detection.
        """

        source_path = Path(path)

        if source_path.suffix.lower() != ".csv":
            return False

        if dataset_type:
            return (
                str(dataset_type).strip().lower()
                == self.dataset_type.lower()
            )

        filename = source_path.name.lower()

        return any(
            token.lower() in filename
            for token in self.filename_tokens
        )

    def load(
        self,
        path: Path,
    ) -> LoaderResult:
        """Load one CSV file into canonical cyclone records."""

        source_path = Path(path).expanduser().resolve()

        if not source_path.exists():
            raise FileNotFoundError(
                f"Dataset file does not exist: {source_path}"
            )

        if not source_path.is_file():
            raise LoaderError(
                f"Dataset source is not a file: {source_path}"
            )

        if source_path.suffix.lower() != ".csv":
            raise LoaderError(
                f"{self.__class__.__name__} only supports CSV files."
            )

        frame = self._read_csv(source_path)

        if frame.empty:
            raise LoaderError(
                f"The dataset contains no rows: {source_path.name}"
            )

        source_columns = list(frame.columns)

        frame = self._normalise_frame_columns(frame)
        columns = self._resolve_columns(frame)

        missing_fields = [
            field
            for field in self.required_fields
            if columns.get(field) is None
        ]

        if missing_fields:
            raise LoaderError(
                f"{source_path.name} is missing required fields: "
                f"{', '.join(missing_fields)}. "
                f"Available columns: {', '.join(frame.columns)}"
            )

        prepared = self._prepare_frame(
            frame,
            columns,
            source_path,
        )

        records = self._build_records(
            prepared,
            source_path,
        )

        if not records:
            raise LoaderError(
                f"No cyclone records could be created from "
                f"{source_path.name}."
            )

        return LoaderResult(
            records=records,
            metadata={
                "dataset_type": self.dataset_type,
                "dataset_label": self.dataset_label,
                "source_file": source_path.name,
                "source_path": str(source_path),
                "source_columns": source_columns,
                "normalised_columns": list(frame.columns),
                "row_count": len(frame),
                "record_count": len(records),
                "tracker_values": sorted(
                    {
                        record.tracker
                        for record in records
                    }
                ),
                "driving_models": sorted(
                    {
                        record.source_model
                        for record in records
                    }
                ),
            },
        )

    def _read_csv(
        self,
        path: Path,
    ) -> pd.DataFrame:
        try:
            return pd.read_csv(
                path,
                low_memory=False,
                na_values=[
                    "",
                    "NA",
                    "N/A",
                    "NaN",
                    "nan",
                    "null",
                    "NULL",
                    "None",
                    "-999",
                    "-9999",
                ],
                keep_default_na=True,
            )
        except UnicodeDecodeError:
            return pd.read_csv(
                path,
                encoding="latin-1",
                low_memory=False,
            )
        except Exception as exc:
            raise LoaderError(
                f"Unable to read {path.name}: {exc}"
            ) from exc

    def _normalise_frame_columns(
        self,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        normalised = frame.copy()

        renamed: dict[object, str] = {}
        used_names: set[str] = set()

        for original_column in normalised.columns:
            base_name = normalise_column_name(
                original_column
            )

            if not base_name:
                base_name = "unnamed"

            unique_name = base_name
            counter = 2

            while unique_name in used_names:
                unique_name = f"{base_name}_{counter}"
                counter += 1

            renamed[original_column] = unique_name
            used_names.add(unique_name)

        normalised = normalised.rename(
            columns=renamed
        )

        unnamed_columns = [
            column
            for column in normalised.columns
            if column.startswith("unnamed")
            and normalised[column].isna().all()
        ]

        if unnamed_columns:
            normalised = normalised.drop(
                columns=unnamed_columns
            )

        return normalised.dropna(
            how="all"
        ).reset_index(drop=True)

    def _resolve_columns(
        self,
        frame: pd.DataFrame,
    ) -> dict[str, Optional[str]]:
        available = set(frame.columns)
        resolved: dict[str, Optional[str]] = {}

        for canonical_name, aliases in self.column_aliases.items():
            resolved[canonical_name] = next(
                (
                    alias
                    for alias in aliases
                    if alias in available
                ),
                None,
            )

        return resolved

    def _prepare_frame(
        self,
        frame: pd.DataFrame,
        columns: Mapping[str, Optional[str]],
        path: Path,
    ) -> pd.DataFrame:
        prepared = pd.DataFrame(
            index=frame.index
        )

        prepared["_source_row"] = (
            frame.index.astype(int) + 2
        )

        prepared["raw_track_id"] = frame[
            columns["track_id"]
        ].map(safe_text)

        prepared["latitude"] = pd.to_numeric(
            frame[columns["latitude"]],
            errors="coerce",
        )

        prepared["longitude"] = pd.to_numeric(
            frame[columns["longitude"]],
            errors="coerce",
        )

        prepared = prepared.dropna(
            subset=[
                "raw_track_id",
                "latitude",
                "longitude",
            ]
        )

        prepared = prepared[
            prepared["raw_track_id"].ne("")
        ].copy()

        prepared["longitude"] = (
            prepared["longitude"]
            .map(self._normalise_longitude)
        )

        driving_model_column = columns.get(
            "driving_model"
        )

        if driving_model_column:
            prepared["driving_model"] = frame.loc[
                prepared.index,
                driving_model_column,
            ].map(
                lambda value: safe_text(
                    value,
                    "unknown",
                )
            )
        else:
            prepared["driving_model"] = "unknown"

        tracker_column = columns.get("tracker")

        if tracker_column:
            prepared["tracker"] = frame.loc[
                prepared.index,
                tracker_column,
            ].map(
                lambda value: safe_text(
                    value,
                    self._tracker_from_filename(path),
                ).upper()
            )
        else:
            prepared["tracker"] = (
                self._tracker_from_filename(path)
            )

        season_column = columns.get("season")

        if season_column:
            prepared["season"] = pd.to_numeric(
                frame.loc[
                    prepared.index,
                    season_column,
                ],
                errors="coerce",
            )
        else:
            prepared["season"] = pd.NA

        year_column = columns.get("year")

        if year_column:
            prepared["year"] = pd.to_numeric(
                frame.loc[
                    prepared.index,
                    year_column,
                ],
                errors="coerce",
            )
        else:
            prepared["year"] = pd.NA

        timestamp_column = columns.get(
            "timestamp"
        )

        if timestamp_column:
            prepared["timestamp"] = pd.to_datetime(
                frame.loc[
                    prepared.index,
                    timestamp_column,
                ],
                errors="coerce",
                utc=True,
            )
        else:
            prepared["timestamp"] = pd.NaT

        timestamp_year = prepared[
            "timestamp"
        ].dt.year

        prepared["season"] = (
            prepared["season"]
            .fillna(prepared["year"])
            .fillna(timestamp_year)
        )

        prepared["year"] = (
            prepared["year"]
            .fillna(prepared["season"])
            .fillna(timestamp_year)
        )

        prepared["season"] = (
            pd.to_numeric(
                prepared["season"],
                errors="coerce",
            )
            .astype("Int64")
        )

        prepared["year"] = (
            pd.to_numeric(
                prepared["year"],
                errors="coerce",
            )
            .astype("Int64")
        )

        segment_column = columns.get("segment")

        if segment_column:
            prepared["segment"] = frame.loc[
                prepared.index,
                segment_column,
            ].map(
                lambda value: safe_text(
                    value,
                    "1",
                )
            )
        else:
            prepared["segment"] = "1"

        step_column = columns.get("step")

        if step_column:
            prepared["step"] = pd.to_numeric(
                frame.loc[
                    prepared.index,
                    step_column,
                ],
                errors="coerce",
            )
        else:
            prepared["step"] = pd.NA

        wind_column = columns.get(
            "wind_speed"
        )

        if wind_column:
            raw_wind = pd.to_numeric(
                frame.loc[
                    prepared.index,
                    wind_column,
                ],
                errors="coerce",
            )

            wind_unit = self._detect_wind_unit(
                wind_column,
                raw_wind,
            )

            prepared["wind_speed"] = (
                self._convert_wind_to_kmh(
                    raw_wind,
                    wind_unit,
                )
            )
        else:
            prepared["wind_speed"] = pd.NA
            wind_unit = "unknown"

        pressure_column = columns.get(
            "pressure"
        )

        if pressure_column:
            pressure = pd.to_numeric(
                frame.loc[
                    prepared.index,
                    pressure_column,
                ],
                errors="coerce",
            )

            prepared["pressure"] = (
                self._normalise_pressure(
                    pressure,
                    pressure_column,
                )
            )
        else:
            prepared["pressure"] = pd.NA

        category_column = columns.get(
            "category"
        )

        if category_column:
            prepared["category"] = (
                frame.loc[
                    prepared.index,
                    category_column,
                ]
                .astype(str)
                .str.extract(
                    r"(\d+)",
                    expand=False,
                )
            )

            prepared["category"] = pd.to_numeric(
                prepared["category"],
                errors="coerce",
            )
        else:
            prepared["category"] = pd.NA

        scenario_column = columns.get(
            "scenario"
        )

        default_scenario = (
            source_scenario_from_filename(path)
        )

        if scenario_column:
            prepared["scenario"] = frame.loc[
                prepared.index,
                scenario_column,
            ].map(
                lambda value: safe_text(
                    value,
                    default_scenario,
                )
            )
        else:
            prepared["scenario"] = (
                default_scenario
            )

        region_column = columns.get("region")

        if region_column:
            prepared["region"] = frame.loc[
                prepared.index,
                region_column,
            ].map(
                lambda value: safe_text(
                    value,
                    self.default_region,
                )
            )
        else:
            prepared["region"] = (
                self.default_region
            )

        landfall_column = columns.get(
            "landfall"
        )

        if landfall_column:
            prepared["landfall"] = frame.loc[
                prepared.index,
                landfall_column,
            ].map(safe_bool)
        else:
            prepared["landfall"] = False

        prepared["_wind_source_unit"] = wind_unit

        return prepared.reset_index(drop=True)

    def _build_records(
        self,
        frame: pd.DataFrame,
        path: Path,
    ) -> list[TCRecord]:
        group_columns = [
            "driving_model",
            "tracker",
            "season",
            "raw_track_id",
            "segment",
        ]

        records: list[TCRecord] = []

        grouped = frame.groupby(
            group_columns,
            sort=False,
            dropna=False,
        )

        for group_key, group in grouped:
            (
                driving_model,
                tracker,
                season,
                raw_track_id,
                segment,
            ) = group_key

            clean_model = safe_text(
                driving_model,
                "unknown",
            )

            clean_tracker = safe_text(
                tracker,
                "unknown",
            ).upper()

            clean_track_id = safe_text(
                raw_track_id,
                "unknown",
            )

            clean_segment = safe_text(
                segment,
                "1",
            )

            season_value = safe_int(season)

            ordered = self._sort_track_rows(
                group
            )

            points = [
                self._build_point(
                    row,
                    point_index,
                )
                for point_index, (_, row) in enumerate(
                    ordered.iterrows()
                )
            ]

            points = [
                point
                for point in points
                if point is not None
            ]

            if not points:
                continue

            first_row = ordered.iloc[0]

            dataset_id = path.stem

            internal_track_id = (
                f"{self.dataset_label.lower()}_"
                f"{clean_tracker.lower()}_"
                f"{clean_model}_"
                f"season-{season_value or 'unknown'}_"
                f"track-{clean_track_id}_"
                f"segment-{clean_segment}"
            )

            record = TCRecord(
                dataset_id=dataset_id,
                track_id=internal_track_id,
                model=self.dataset_label,
                driving_model=clean_model,
                tracker=clean_tracker,
                scenario=safe_text(
                    first_row.get("scenario"),
                    "unknown",
                ),
                region=safe_text(
                    first_row.get("region"),
                    self.default_region,
                ),
                season=season_value,
                year=safe_int(
                    first_row.get("year")
                ),
                points=points,
                landfall=bool(
                    ordered["landfall"].any()
                ),
                metadata={
                    "raw_track_id": clean_track_id,
                    "segment_id": clean_segment,
                    "season": season_value,
                    "source_model_value": clean_model,
                    "source_file": path.name,
                    "source_dataset_type": (
                        self.dataset_type
                    ),
                    "source_scenario": safe_text(
                        first_row.get("scenario"),
                        "unknown",
                    ),
                    "source_row_start": safe_int(
                        ordered["_source_row"].min()
                    ),
                    "source_row_end": safe_int(
                        ordered["_source_row"].max()
                    ),
                    "source_point_count": len(
                        ordered
                    ),
                    "source_wind_unit": safe_text(
                        first_row.get(
                            "_wind_source_unit"
                        ),
                        "unknown",
                    ),
                },
            )

            record.refresh_derived_fields()
            records.append(record)

        return records

    def _build_point(
        self,
        row: pd.Series,
        point_index: int,
    ) -> Optional[TrackPoint]:
        latitude = safe_float(
            row.get("latitude")
        )

        longitude = safe_float(
            row.get("longitude")
        )

        if latitude is None or longitude is None:
            return None

        timestamp = safe_datetime(
            row.get("timestamp")
        )

        source_step = safe_int(
            row.get("step")
        )

        return TrackPoint(
            lat=latitude,
            lon=longitude,
            timestamp=timestamp,
            wind_speed=safe_float(
                row.get("wind_speed")
            ),
            pressure=safe_float(
                row.get("pressure")
            ),
            category=safe_int(
                row.get("category")
            ),
            step=(
                source_step
                if source_step is not None
                else point_index
            ),
            metadata={
                "source_row": safe_int(
                    row.get("_source_row")
                ),
            },
        )

    def _sort_track_rows(
        self,
        frame: pd.DataFrame,
    ) -> pd.DataFrame:
        ordered = frame.copy()

        ordered["_sort_step"] = pd.to_numeric(
            ordered["step"],
            errors="coerce",
        )

        ordered["_sort_time"] = pd.to_datetime(
            ordered["timestamp"],
            errors="coerce",
            utc=True,
        )

        if ordered["_sort_time"].notna().any():
            ordered = ordered.sort_values(
                [
                    "_sort_time",
                    "_sort_step",
                    "_source_row",
                ],
                kind="stable",
                na_position="last",
            )
        elif ordered["_sort_step"].notna().any():
            ordered = ordered.sort_values(
                [
                    "_sort_step",
                    "_source_row",
                ],
                kind="stable",
                na_position="last",
            )
        else:
            ordered = ordered.sort_values(
                "_source_row",
                kind="stable",
            )

        return ordered.drop(
            columns=[
                "_sort_step",
                "_sort_time",
            ]
        )

    def _tracker_from_filename(
        self,
        path: Path,
    ) -> str:
        filename = path.stem.lower()

        if re.search(r"(^|_)cdd($|_)", filename):
            return "CDD"

        if re.search(r"(^|_)te($|_)", filename):
            return "TE"

        return "UNKNOWN"

    def _detect_wind_unit(
        self,
        column_name: str,
        values: pd.Series,
    ) -> str:
        configured = (
            self.default_wind_unit
            .strip()
            .lower()
        )

        if configured != "auto":
            return configured

        normalised_name = normalise_column_name(
            column_name
        )

        if any(
            token in normalised_name
            for token in (
                "kmh",
                "km_h",
                "kph",
            )
        ):
            return "km/h"

        if any(
            token in normalised_name
            for token in (
                "mps",
                "m_s",
                "_ms",
            )
        ):
            return "m/s"

        if any(
            token in normalised_name
            for token in (
                "knot",
                "_kt",
                "knots",
            )
        ):
            return "knots"

        valid_values = pd.to_numeric(
            values,
            errors="coerce",
        ).dropna()

        if valid_values.empty:
            return "km/h"

        percentile_99 = float(
            valid_values.quantile(0.99)
        )

        # Tropical cyclone winds expressed in m/s are normally much smaller
        # numerically than the equivalent km/h values.
        if percentile_99 <= 100:
            return "m/s"

        return "km/h"

    def _convert_wind_to_kmh(
        self,
        values: pd.Series,
        unit: str,
    ) -> pd.Series:
        normalised_unit = (
            unit.strip().lower()
        )

        numeric = pd.to_numeric(
            values,
            errors="coerce",
        )

        if normalised_unit in {
            "m/s",
            "ms",
            "mps",
        }:
            return numeric * 3.6

        if normalised_unit in {
            "kt",
            "kts",
            "knot",
            "knots",
        }:
            return numeric * 1.852

        if normalised_unit == "mph":
            return numeric * 1.609344

        return numeric

    def _normalise_pressure(
        self,
        values: pd.Series,
        column_name: str,
    ) -> pd.Series:
        numeric = pd.to_numeric(
            values,
            errors="coerce",
        )

        normalised_name = normalise_column_name(
            column_name
        )

        if normalised_name.endswith("_pa"):
            return numeric / 100.0

        valid_values = numeric.dropna()

        if (
            not valid_values.empty
            and float(valid_values.median()) > 2_000
        ):
            return numeric / 100.0

        return numeric

    @staticmethod
    def _normalise_longitude(
        longitude: object,
    ) -> float:
        value = float(longitude)

        while value > 180:
            value -= 360

        while value < -180:
            value += 360

        return value